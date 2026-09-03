#!/usr/bin/env python3
"""Evaluate preregistered C-27 concentrated-aggressor exhaustion."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

LOOKBACK=2880; SHARE_Q=.99; IMBALANCE_Q=.95; IMBALANCE_FLOOR=.30
HOLD_BARS=16; PRIMARY_COST=.003; COSTS=(.002,.003,.005)
PRIMARY_START,PRIMARY_END=1735689600,1788134400
REVERSE_START,REVERSE_END=1704067200,1735689600

def load_panel(path):
    return pd.read_csv(path).sort_values('timestamp').drop_duplicates('timestamp')

def load_price(path):
    return pd.read_csv(path,usecols=['timestamp','open']).sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')

def load_funding(path):
    return pd.read_csv(path).sort_values('timestamp').drop_duplicates('timestamp')

def causal_features(panel):
    f=panel.copy().sort_values('timestamp').reset_index(drop=True)
    prior_share=f.top_1pct_quote_share.shift(1)
    prior_imb=f.signed_imbalance.abs().shift(1)
    f['share_threshold']=prior_share.rolling(LOOKBACK,min_periods=LOOKBACK).quantile(SHARE_Q)
    f['imbalance_threshold']=prior_imb.rolling(LOOKBACK,min_periods=LOOKBACK).quantile(IMBALANCE_Q)
    return f

def collect_events(features,price,funding,start,end):
    events=[];last_exit=-1
    census={'period_rows':0,'warmup_rejected':0,'concentration_rejected':0,'imbalance_rejected':0,
            'missing_path':0,'overlap_rejected':0,'signals':0}
    for row in features.itertuples(index=False):
        signal_ts=int(row.timestamp);entry_ts=signal_ts+900
        if not start<=entry_ts<end:continue
        census['period_rows']+=1
        if pd.isna(row.share_threshold) or pd.isna(row.imbalance_threshold):census['warmup_rejected']+=1;continue
        if not float(row.top_1pct_quote_share)>float(row.share_threshold):census['concentration_rejected']+=1;continue
        imbalance=float(row.signed_imbalance)
        if not (abs(imbalance)>float(row.imbalance_threshold) and abs(imbalance)>IMBALANCE_FLOOR):census['imbalance_rejected']+=1;continue
        census['signals']+=1;exit_ts=entry_ts+HOLD_BARS*900
        expected=[entry_ts+i*900 for i in range(HOLD_BARS+1)]
        if any(t not in price.index for t in expected):census['missing_path']+=1;continue
        if entry_ts<last_exit:census['overlap_rejected']+=1;continue
        side='SHORT' if imbalance>0 else 'LONG';entry=float(price.loc[entry_ts,'open']);exit_=float(price.loc[exit_ts,'open'])
        price_return=(exit_/entry-1)*(1 if side=='LONG' else -1)
        rates=funding.loc[(funding.timestamp>entry_ts)&(funding.timestamp<=exit_ts),'funding_rate'].sum()
        funding_return=float(rates)*(-1 if side=='LONG' else 1);gross=price_return+funding_return
        events.append({'side':side,'signal_timestamp':signal_ts,'entry_timestamp':entry_ts,'exit_timestamp':exit_ts,
          'signed_imbalance':imbalance,'imbalance_threshold':float(row.imbalance_threshold),
          'top_1pct_quote_share':float(row.top_1pct_quote_share),'share_threshold':float(row.share_threshold),
          'entry_price':entry,'exit_price':exit_,'price_return':price_return,'funding_return':funding_return,'gross_return':gross})
        last_exit=exit_ts
    return events,census

def assign_folds(events):
    ts=sorted(e['entry_timestamp'] for e in events)
    if not ts:return
    bounds=[ts[i*len(ts)//4] for i in range(4)]
    for e in events:e['fold']=max(i for i,b in enumerate(bounds) if e['entry_timestamp']>=b)+1

def metrics(events,cost=PRIMARY_COST):
    v=np.asarray([e['gross_return']-cost for e in events])
    if not len(v):return {'n':0,'expectancy':None,'profit_factor':None,'win_rate':None,'max_drawdown':None}
    wins,losses=v[v>0],v[v<=0];eq=v.cumsum();peak=np.maximum.accumulate(np.r_[0.,eq])[1:]
    return {'n':int(len(v)),'expectancy':float(v.mean()),'profit_factor':float(wins.sum()/-losses.sum()) if len(losses) and losses.sum() else None,
      'win_rate':float((v>0).mean()),'max_drawdown':float((peak-eq).max(initial=0))}

def bootstrap(events,samples=10000):
    if not events:return [None,None]
    clusters={}
    for e in events:clusters.setdefault(e['entry_timestamp']//86400,[]).append(e['gross_return']-PRIMARY_COST)
    keys=sorted(clusters);rng=np.random.default_rng(270027);out=np.empty(samples)
    for i in range(samples):
        chosen=rng.choice(keys,len(keys),replace=True);out[i]=np.mean([v for k in chosen for v in clusters[int(k)]])
    return [float(x) for x in np.quantile(out,[.025,.975])]

def summary(events):
    years=sorted({pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year for e in events})
    return {'overall':metrics(events),'clustered_bootstrap_95_ci':bootstrap(events),
      'by_fold':{f'F{i}':metrics([e for e in events if e.get('fold')==i]) for i in range(1,5)},
      'by_side':{s:metrics([e for e in events if e['side']==s]) for s in ('LONG','SHORT')},
      'by_year':{str(y):metrics([e for e in events if pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year==y]) for y in years},
      'cost_sensitivity':{f'{c:.3f}':metrics(events,c) for c in COSTS},
      'mean_abs_imbalance':float(np.mean([abs(e['signed_imbalance']) for e in events])) if events else None,
      'mean_top_1pct_share':float(np.mean([e['top_1pct_quote_share'] for e in events])) if events else None,
      'mean_funding_return':float(np.mean([e['funding_return'] for e in events])) if events else None}

def monthly_positive_concentration(events):
    values={}
    for e in events:
        month=pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).strftime('%Y-%m')
        values[month]=values.get(month,0)+max(0,e['gross_return']-PRIMARY_COST)
    total=sum(values.values());return max(values.values(),default=0)/total if total else None

def build_report(panel_path,price_path,funding_path):
    features=causal_features(load_panel(panel_path));price=load_price(price_path);funding=load_funding(funding_path)
    pe,pc=collect_events(features,price,funding,PRIMARY_START,PRIMARY_END);re,rc=collect_events(features,price,funding,REVERSE_START,REVERSE_END)
    assign_folds(pe);assign_folds(re);p,r=summary(pe),summary(re);conc=monthly_positive_concentration(pe);o=p['overall']
    years=p['by_year'];checks={'primary_n':o['n']>=200,'primary_positive':o['expectancy'] is not None and o['expectancy']>0,
      'primary_pf':o['profit_factor'] is not None and o['profit_factor']>1,'bootstrap':p['clustered_bootstrap_95_ci'][0] is not None and p['clustered_bootstrap_95_ci'][0]>0,
      'folds':sum(v['n']>=30 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_fold'].values())>=3,
      'sides':all(v['n']>=60 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_side'].values()),
      'years':all(years.get(str(y),{'n':0})['n']>=50 and years[str(y)]['expectancy']>0 for y in (2025,2026)),
      'concentration':conc is not None and conc<=.25,
      'reverse':r['overall']['n']>=100 and r['overall']['expectancy'] is not None and r['overall']['expectancy']>0 and r['overall']['profit_factor'] is not None and r['overall']['profit_factor']>1,
      'cost_005':p['cost_sensitivity']['0.005']['expectancy'] is not None and p['cost_sensitivity']['0.005']['expectancy']>0}
    return {'candidate':'C-27','protocol':'edge-candidate-register-v26','primary_census':pc,'reverse_census':rc,'primary':p,'reverse':r,
      'max_positive_pnl_month_concentration':conc,'gate':{'checks':checks,'verdict':'KEEP_FOR_PROSPECTIVE_VALIDATION' if all(checks.values()) else 'REJECT'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--panel',default='data/research/btc_aggtrades/normalized/BTCUSDT.csv.gz');p.add_argument('--price',default='data/research/c06/binance_futures_15m/BTCUSDT.csv');p.add_argument('--funding',default='data/research/c16/funding/BTCUSDT.csv');p.add_argument('--output',default='docs/reports/edge_candidate_c27.json');a=p.parse_args()
    report=build_report(Path(a.panel),Path(a.price),Path(a.funding));rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False);target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rendered+'\n');print(rendered)
if __name__=='__main__':main()
