#!/usr/bin/env python3
"""Evaluate preregistered C-29 top-trader/crowd positioning divergence."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

SYMBOLS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT")
DECISION=14400; METRIC_LAG=300; WARMUP=180; HOLD=86400; PRIMARY_COST=.003; COSTS=(.002,.003,.005)
PRIMARY_START,PRIMARY_END=1672531200,1788134400
REVERSE_START,REVERSE_END=1638316800,1672531200
METRIC_HASH={"BTCUSDT":"1eb3cf846545e975f2be6ed32bc49a0333a6f7d07e4125c623bbc6fc12adbce6","ETHUSDT":"5eb10e69e01ad26f02cbf0164eaea6cc7348d80f698d3d285db25ff737cffc11","BNBUSDT":"910cbb0644779fda188c24eedb302b30a14c54a517208d9b226a8ac40dea582d","XRPUSDT":"64aaf6be57a3036687319c043f5a7da08e4ee385a07c2d72d0089cbba35996fe","ADAUSDT":"0c1c29430a77e04c96a4c35c99bbb0f6b4400787fee0641f26bc10739a031d53","SOLUSDT":"8aec2bcdfcc72c23cd88d6cb0a54f886eead0d5f345e6549632ddf14938b1718"}
PRIMARY_PRICE_HASH={"BTCUSDT":"30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb","ETHUSDT":"d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843","BNBUSDT":"7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0","XRPUSDT":"89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57","ADAUSDT":"643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a","SOLUSDT":"e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382"}
REVERSE_PRICE_HASH={"BTCUSDT":"acf4a7f5c58733f6db5e39e74387a9ab5a08ecc17a4600e8074555571b33fc09","ETHUSDT":"378bb36782172ee5cc4d3d7a983c674ecc09f0c38ddb35007aced58e437d0a54","BNBUSDT":"e0987b51c7efb509645bb15b636b889d3433c4b47e0ca21e796918ec4da60da5","XRPUSDT":"91003b36b91f2202066bf12456dd12f2103d79f7691b0b009a0b4de4767e12a2","ADAUSDT":"7ac7ca870083326197e5e977dc31db6abc5336814b3c3512781088145c722ef1","SOLUSDT":"833b7f033ccd5eb86eb11730d019b1f5c84021689ef7dfd9dafda0bff0f0a449"}
FUNDING_HASH={"BTCUSDT":"2fe89ca06907e7953cb49c2db052e74158ea9319f50f0bd9dac08fb2a579c097","ETHUSDT":"b978d9a54809ad232583b9419ed2695647d0557bc58074112082fa1472057148","BNBUSDT":"7edf30b5a20f5572361ba7bc41ff89b02df8105a82ff24c1b32a5dc807bca08d","XRPUSDT":"2886be913f6678b660e827d481a2b60d426de6c8b406bcff3c282d3f275e74f9","ADAUSDT":"f27f351e603c0563d9c1e0ea6be10640a8bf38c4a1640383d914cd5aaaa79301","SOLUSDT":"be28b9621e6baf0d3b50365c73e59352996274f4097cae60fe4ffce2528c55a3"}

def verify(path,expected):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected: raise ValueError(f"frozen source hash mismatch: {path}")
def load_price(path): return pd.read_csv(path,usecols=['timestamp','open']).sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')
def load_funding(path): return pd.read_csv(path).sort_values('timestamp').drop_duplicates('timestamp')
def load_metrics(path):
    f=pd.read_csv(path,usecols=['create_time','count_long_short_ratio','sum_toptrader_long_short_ratio'])
    f['timestamp']=pd.to_datetime(f.create_time,utc=True).astype('int64')//10**9
    return f.sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')
def causal_features(price,metrics):
    rows=[]
    for ts in price.index:
        ts=int(ts)
        if ts%DECISION or ts-METRIC_LAG not in metrics.index: continue
        r=metrics.loc[ts-METRIC_LAG]; crowd=float(r.count_long_short_ratio); top=float(r.sum_toptrader_long_short_ratio)
        if not (np.isfinite(crowd) and np.isfinite(top) and crowd>0 and top>0): continue
        crowd,top=np.log(crowd),np.log(top); rows.append({'decision_timestamp':ts,'crowd':crowd,'top':top,'divergence':abs(top-crowd)})
    f=pd.DataFrame(rows).set_index('decision_timestamp') if rows else pd.DataFrame(columns=['crowd','top','divergence'])
    f['crowd_threshold']=f.crowd.abs().shift(1).rolling(WARMUP,min_periods=WARMUP).quantile(.90)
    f['divergence_threshold']=f.divergence.shift(1).rolling(WARMUP,min_periods=WARMUP).quantile(.90)
    return f
def collect(symbol,features,price,funding,start,end):
    events=[];last_exit=-1;c={k:0 for k in ('period_rows','warmup_rejected','same_side_rejected','threshold_rejected','missing_path','overlap_rejected','signals')}
    for ts,r in features.iterrows():
        ts=int(ts)
        if not start<=ts<end: continue
        c['period_rows']+=1
        if pd.isna(r.crowd_threshold) or pd.isna(r.divergence_threshold): c['warmup_rejected']+=1;continue
        if not r.crowd*r.top<0: c['same_side_rejected']+=1;continue
        if not (abs(r.crowd)>r.crowd_threshold and r.divergence>r.divergence_threshold): c['threshold_rejected']+=1;continue
        c['signals']+=1; exit_ts=ts+HOLD
        if any(ts+i*900 not in price.index for i in range(HOLD//900+1)): c['missing_path']+=1;continue
        if ts<last_exit: c['overlap_rejected']+=1;continue
        side='LONG' if r.top>0 else 'SHORT'; direction=1 if side=='LONG' else -1
        entry=float(price.loc[ts,'open']);exit_price=float(price.loc[exit_ts,'open']);price_return=direction*(exit_price/entry-1)
        rates=funding.loc[(funding.timestamp>ts)&(funding.timestamp<=exit_ts),'funding_rate'].sum();funding_return=-direction*float(rates)
        events.append({'symbol':symbol,'side':side,'entry_timestamp':ts,'exit_timestamp':exit_ts,'crowd_log_ratio':float(r.crowd),'top_log_ratio':float(r.top),'divergence':float(r.divergence),'gross_return':price_return+funding_return,'price_return':price_return,'funding_return':funding_return});last_exit=exit_ts
    return events,c
def metrics(events,cost=PRIMARY_COST):
    v=np.asarray([e['gross_return']-cost for e in events])
    if not len(v): return {'n':0,'expectancy':None,'profit_factor':None,'win_rate':None,'max_drawdown':None}
    w,l=v[v>0],v[v<=0];eq=v.cumsum();peak=np.maximum.accumulate(np.r_[0.,eq])[1:]
    return {'n':int(len(v)),'expectancy':float(v.mean()),'profit_factor':float(w.sum()/-l.sum()) if len(l) and l.sum() else None,'win_rate':float((v>0).mean()),'max_drawdown':float((peak-eq).max(initial=0))}
def assign_folds(events):
    ts=sorted(e['entry_timestamp'] for e in events)
    if not ts:return []
    bounds=[ts[i*len(ts)//4] for i in range(4)]+[max(ts)+HOLD+1]
    kept=[]
    for e in events:
        i=max(i for i,b in enumerate(bounds[:-1]) if e['entry_timestamp']>=b)
        if e['exit_timestamp']<bounds[i+1]: e['fold']=i+1;kept.append(e)
    return kept
def bootstrap(events):
    if not events:return [None,None]
    clusters={}
    for e in events:clusters.setdefault(e['entry_timestamp']//86400,[]).append(e['gross_return']-PRIMARY_COST)
    keys=sorted(clusters);rng=np.random.default_rng(290029);out=[]
    for _ in range(10000):
        chosen=rng.choice(keys,len(keys),replace=True);out.append(np.mean([v for k in chosen for v in clusters[int(k)]]))
    return [float(x) for x in np.quantile(out,[.025,.975])]
def summary(events):
    years=sorted({pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year for e in events})
    return {'overall':metrics(events),'clustered_bootstrap_95_ci':bootstrap(events),'by_fold':{f'F{i}':metrics([e for e in events if e.get('fold')==i]) for i in range(1,5)},'by_side':{s:metrics([e for e in events if e['side']==s]) for s in ('LONG','SHORT')},'by_symbol':{s:metrics([e for e in events if e['symbol']==s]) for s in SYMBOLS},'by_year':{str(y):metrics([e for e in events if pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year==y]) for y in years},'cost_sensitivity':{f'{c:.3f}':metrics(events,c) for c in COSTS},'mean_funding_return':float(np.mean([e['funding_return'] for e in events])) if events else None}
def build_report(primary_dir,reverse_dir,metric_dir,funding_dir):
    pe=[];re=[];pc={};rc={}
    for s in SYMBOLS:
        pp=primary_dir/f'{s}.csv';rp=reverse_dir/f'{s}.csv';mp=metric_dir/f'{s}.csv.gz';fp=funding_dir/f'{s}.csv'
        for p,h in ((pp,PRIMARY_PRICE_HASH[s]),(rp,REVERSE_PRICE_HASH[s]),(mp,METRIC_HASH[s]),(fp,FUNDING_HASH[s])):verify(p,h)
        m=load_metrics(mp);fund=load_funding(fp)
        selected,c=collect(s,causal_features(load_price(pp),m),load_price(pp),fund,PRIMARY_START,PRIMARY_END);pe+=selected;pc[s]=c
        selected,c=collect(s,causal_features(load_price(rp),m),load_price(rp),fund,REVERSE_START,REVERSE_END);re+=selected;rc[s]=c
    pe=assign_folds(pe);assign_folds(re);p=summary(pe);r=summary(re)
    positive={s:sum(max(0,e['gross_return']-PRIMARY_COST) for e in pe if e['symbol']==s) for s in SYMBOLS};total=sum(positive.values());conc=max(positive.values(),default=0)/total if total else None;o=p['overall']
    checks={'primary_n':o['n']>=300,'primary_positive':o['expectancy'] is not None and o['expectancy']>0,'primary_pf':o['profit_factor'] is not None and o['profit_factor']>1,'bootstrap':p['clustered_bootstrap_95_ci'][0] is not None and p['clustered_bootstrap_95_ci'][0]>0,'folds':sum(v['n']>=50 and v['expectancy']>0 for v in p['by_fold'].values())>=3,'sides':all(v['n']>=75 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_side'].values()),'symbols':sum(v['n']>=40 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_symbol'].values())>=4,'years':all(p['by_year'].get(str(y),{'n':0})['n']>=50 and p['by_year'][str(y)]['expectancy']>0 for y in (2023,2024,2025,2026)),'concentration':conc is not None and conc<=.35,'reverse':r['overall']['n']>=150 and r['overall']['expectancy'] is not None and r['overall']['expectancy']>0 and r['overall']['profit_factor'] is not None and r['overall']['profit_factor']>1,'cost_005':p['cost_sensitivity']['0.005']['expectancy'] is not None and p['cost_sensitivity']['0.005']['expectancy']>0}
    return {'candidate':'C-29','protocol':'edge-candidate-register-v28','primary_census':pc,'reverse_census':rc,'primary':p,'reverse':r,'max_positive_pnl_symbol_concentration':conc,'gate':{'checks':checks,'verdict':'KEEP_FOR_PROSPECTIVE_VALIDATION' if all(checks.values()) else 'REJECT'}}
def main():
    a=argparse.ArgumentParser();a.add_argument('--primary-price-dir',default='data/research/c06/binance_futures_15m');a.add_argument('--reverse-price-dir',default='data/research/c09/binance_futures_15m');a.add_argument('--metric-dir',default='data/research/oi_metrics/normalized');a.add_argument('--funding-dir',default='data/research/c16/funding');a.add_argument('--output',default='docs/reports/edge_candidate_c29.json');x=a.parse_args();report=build_report(Path(x.primary_price_dir),Path(x.reverse_price_dir),Path(x.metric_dir),Path(x.funding_dir));rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False);target=Path(x.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rendered+'\n');print(rendered)
if __name__=='__main__':main()
