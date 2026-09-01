#!/usr/bin/env python3
"""Evaluate preregistered C-26 BTC-lead / alt-underreaction."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

ALTS=("ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT")
PRIMARY_START,PRIMARY_END=1704067200,1788134400
REVERSE_START,REVERSE_END=1672531200,1704067200
LOOKBACK=720; SHOCK_FLOOR=.015; RESPONSE_MAX=.35; HOLD_BARS=16; PRIMARY_COST=.003; COSTS=(.002,.003,.005)

def load_price(path):
    f=pd.read_csv(path,usecols=['timestamp','open','close']).sort_values('timestamp').drop_duplicates('timestamp')
    return f.set_index('timestamp')

def completed_hours(price):
    rows=[]
    for hour,group in price.reset_index().groupby(price.reset_index()['timestamp']//3600,sort=True):
        g=group.sort_values('timestamp'); expected=[hour*3600+i*900 for i in range(4)]
        if g.timestamp.astype(int).tolist()!=expected: continue
        rows.append({'timestamp':hour*3600+3600,'return':float(g.iloc[-1].close/g.iloc[0].open-1)})
    return pd.DataFrame(rows)

def btc_context(price):
    f=completed_hours(price); f['threshold']=f['return'].abs().shift(1).rolling(LOOKBACK,min_periods=LOOKBACK).quantile(.95); return f

def load_funding(path):
    return pd.read_csv(path).sort_values('timestamp').drop_duplicates('timestamp')

def symbol_events(symbol,btc,alt_hours,alt_price,funding,start,end):
    merged=btc.merge(alt_hours,on='timestamp',suffixes=('_btc','_alt'),validate='one_to_one'); events=[]; last_exit=-1
    census={'aligned_hours':0,'warmup_rejected':0,'non_shock':0,'non_underreaction':0,'missing_path':0,'overlap_rejected':0}
    for row in merged.itertuples(index=False):
        ts=int(row.timestamp)
        if not start<=ts<end: continue
        census['aligned_hours']+=1
        if pd.isna(row.threshold): census['warmup_rejected']+=1; continue
        br=float(row.return_btc); ar=float(row.return_alt)
        if not (abs(br)>SHOCK_FLOOR and abs(br)>float(row.threshold)): census['non_shock']+=1; continue
        ratio=ar/br
        if not 0<=ratio<=RESPONSE_MAX: census['non_underreaction']+=1; continue
        entry_ts=ts; exit_ts=entry_ts+HOLD_BARS*900
        expected=[entry_ts+i*900 for i in range(HOLD_BARS+1)]
        if any(t not in alt_price.index for t in expected): census['missing_path']+=1; continue
        if entry_ts<last_exit: census['overlap_rejected']+=1; continue
        side='LONG' if br>0 else 'SHORT'; entry=float(alt_price.loc[entry_ts,'open']); exit_=float(alt_price.loc[exit_ts,'open'])
        price_return=(exit_/entry-1)*(1 if side=='LONG' else -1)
        rates=funding.loc[(funding.timestamp>entry_ts)&(funding.timestamp<=exit_ts),'funding_rate'].sum()
        funding_return=float(rates)*(-1 if side=='LONG' else 1); gross=price_return+funding_return
        events.append({'symbol':symbol,'side':side,'signal_timestamp':ts,'entry_timestamp':entry_ts,'exit_timestamp':exit_ts,
          'btc_return':br,'alt_signal_return':ar,'response_ratio':ratio,'threshold':float(row.threshold),
          'entry_price':entry,'exit_price':exit_,'price_return':price_return,'funding_return':funding_return,'gross_return':gross})
        last_exit=exit_ts
    return events,census

def assign_folds(events):
    ts=sorted(e['entry_timestamp'] for e in events)
    if not ts:return
    b=[ts[i*len(ts)//4] for i in range(4)]
    for e in events:e['fold']=max(i for i,x in enumerate(b) if e['entry_timestamp']>=x)+1

def metrics(events,cost=PRIMARY_COST):
    v=np.asarray([e['gross_return']-cost for e in events])
    if not len(v):return {'n':0,'expectancy':None,'profit_factor':None,'win_rate':None,'max_drawdown':None}
    w,l=v[v>0],v[v<=0]; eq=v.cumsum(); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]
    return {'n':int(len(v)),'expectancy':float(v.mean()),'profit_factor':float(w.sum()/-l.sum()) if len(l) and l.sum() else None,
      'win_rate':float((v>0).mean()),'max_drawdown':float((peak-eq).max(initial=0))}

def bootstrap(events,samples=10000):
    if not events:return [None,None]
    clusters={}
    for e in events:clusters.setdefault(e['signal_timestamp'],[]).append(e['gross_return']-PRIMARY_COST)
    keys=sorted(clusters); rng=np.random.default_rng(260026); out=np.empty(samples)
    for i in range(samples):
        chosen=rng.choice(keys,len(keys),replace=True); out[i]=np.mean([v for k in chosen for v in clusters[int(k)]])
    return [float(x) for x in np.quantile(out,[.025,.975])]

def collect(price_dir,funding_dir,start,end):
    btc=btc_context(load_price(price_dir/'BTCUSDT.csv')); events=[]; census={}
    for s in ALTS:
        price=load_price(price_dir/f'{s}.csv'); selected,counts=symbol_events(s,btc,completed_hours(price),price,load_funding(funding_dir/f'{s}.csv'),start,end); events+=selected; census[s]=counts
    assign_folds(events); return events,census

def summary(events):
    years=sorted({pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year for e in events})
    return {'overall':metrics(events),'clustered_bootstrap_95_ci':bootstrap(events),
      'by_fold':{f'F{i}':metrics([e for e in events if e['fold']==i]) for i in range(1,5)},
      'by_side':{side:metrics([e for e in events if e['side']==side]) for side in ('LONG','SHORT')},
      'by_symbol':{s:metrics([e for e in events if e['symbol']==s]) for s in ALTS},
      'by_year':{str(y):metrics([e for e in events if pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year==y]) for y in years},
      'cost_sensitivity':{f'{c:.3f}':metrics(events,c) for c in COSTS},
      'mean_btc_shock':float(np.mean([abs(e['btc_return']) for e in events])) if events else None,
      'mean_response_ratio':float(np.mean([e['response_ratio'] for e in events])) if events else None,
      'mean_funding_return':float(np.mean([e['funding_return'] for e in events])) if events else None}

def build_report(price_dir,funding_dir):
    pe,pc=collect(price_dir,funding_dir,PRIMARY_START,PRIMARY_END); re,rc=collect(price_dir,funding_dir,REVERSE_START,REVERSE_END); p,r=summary(pe),summary(re)
    positive={s:sum(max(0,e['gross_return']-PRIMARY_COST) for e in pe if e['symbol']==s) for s in ALTS}; total=sum(positive.values()); conc=max(positive.values(),default=0)/total if total else None
    o=p['overall']; checks={'primary_n':o['n']>=400,'primary_positive':o['expectancy'] is not None and o['expectancy']>0,'primary_pf':o['profit_factor'] is not None and o['profit_factor']>1,
      'bootstrap':p['clustered_bootstrap_95_ci'][0] is not None and p['clustered_bootstrap_95_ci'][0]>0,
      'folds':sum(v['n']>=60 and v['expectancy']>0 for v in p['by_fold'].values())>=3,
      'sides':all(v['n']>=100 and v['expectancy']>0 for v in p['by_side'].values()),
      'symbols':sum(v['n']>=50 and v['expectancy']>0 for v in p['by_symbol'].values())>=4,
      'concentration':conc is not None and conc<=.35,
      'reverse':r['overall']['n']>=100 and r['overall']['expectancy']>0 and r['overall']['profit_factor']>1,
      'cost_005':p['cost_sensitivity']['0.005']['expectancy'] is not None and p['cost_sensitivity']['0.005']['expectancy']>0}
    return {'candidate':'C-26','protocol':'edge-candidate-register-v25','primary_census':pc,'reverse_census':rc,'primary':p,'reverse':r,'max_positive_pnl_symbol_concentration':conc,'gate':{'checks':checks,'verdict':'KEEP_FOR_PROSPECTIVE_VALIDATION' if all(checks.values()) else 'REJECT'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--price-dir',default='data/research/c06/binance_futures_15m');p.add_argument('--funding-dir',default='data/research/c16/funding');p.add_argument('--output',default='docs/reports/edge_candidate_c26.json');a=p.parse_args();report=build_report(Path(a.price_dir),Path(a.funding_dir));rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False);target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rendered+'\n');print(rendered)
if __name__=='__main__':main()
