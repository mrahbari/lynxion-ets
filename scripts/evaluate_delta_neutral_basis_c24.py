#!/usr/bin/env python3
"""Evaluate preregistered C-24 delta-neutral spot/perpetual basis convergence."""

from __future__ import annotations

import argparse, gzip, json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

SYMBOLS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT")
PRIMARY_START,PRIMARY_END=1704067200,1788134400
REVERSE_START,REVERSE_END=1672531200,1704067200
LOOKBACK=2880; FLOOR=0.004; CONVERGED=0.0005; TIMEOUT=96; PRIMARY_COST=0.002
COSTS=(0.0015,0.002,0.003,0.005)

def load_panel(path:Path,prefix:str)->pd.DataFrame:
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt') as handle: f=pd.read_csv(handle,usecols=['timestamp','open','close'])
    f=f.sort_values('timestamp').drop_duplicates('timestamp')
    return f.rename(columns={'open':f'{prefix}_open','close':f'{prefix}_close'})

def aligned_basis(spot_path:Path,perp_path:Path)->pd.DataFrame:
    f=load_panel(spot_path,'spot').merge(load_panel(perp_path,'perp'),on='timestamp',how='inner',validate='one_to_one')
    f['basis']=f['perp_close']/f['spot_close']-1
    f['threshold']=f['basis'].shift(1).rolling(LOOKBACK,min_periods=LOOKBACK).quantile(.99)
    return f.reset_index(drop=True)

def load_funding(path:Path)->pd.DataFrame:
    f=pd.read_csv(path).sort_values('timestamp').drop_duplicates('timestamp'); f['funding_rate']=pd.to_numeric(f['funding_rate'])
    return f

def symbol_events(symbol:str,panel:pd.DataFrame,funding:pd.DataFrame,start:int,end:int):
    events=[]; last_exit=-1
    census={'completed_bars':0,'warmup_rejected':0,'non_signal':0,'missing_next_open':0,'overlap_rejected':0,'timeouts':0}
    for i in range(len(panel)-1):
        row=panel.iloc[i]; ts=int(row.timestamp)
        if not start<=ts<end: continue
        census['completed_bars']+=1
        if pd.isna(row.threshold): census['warmup_rejected']+=1; continue
        if not (float(row.basis)>FLOOR and float(row.basis)>float(row.threshold)):
            census['non_signal']+=1; continue
        entry_i=i+1; entry_ts=int(panel.iloc[entry_i].timestamp)
        if entry_ts!=ts+900: census['missing_next_open']+=1; continue
        if entry_ts<last_exit: census['overlap_rejected']+=1; continue
        trigger_i=None
        limit=min(entry_i+TIMEOUT,len(panel)-1)
        for j in range(entry_i,limit):
            if int(panel.iloc[j+1].timestamp)!=int(panel.iloc[j].timestamp)+900: break
            if float(panel.iloc[j].basis)<=CONVERGED: trigger_i=j; break
        timed_out=trigger_i is None
        exit_i=entry_i+TIMEOUT if timed_out else trigger_i+1
        if exit_i>=len(panel) or int(panel.iloc[exit_i].timestamp)!=entry_ts+(exit_i-entry_i)*900:
            census['missing_next_open']+=1; continue
        exit_ts=int(panel.iloc[exit_i].timestamp)
        if exit_ts>=end: census['missing_next_open']+=1; continue
        entry=panel.iloc[entry_i]; exit_=panel.iloc[exit_i]
        spot_return=float(exit_.spot_open/entry.spot_open-1)
        perp_return=float((entry.perp_open-exit_.perp_open)/entry.perp_open)
        rates=funding.loc[(funding.timestamp>entry_ts)&(funding.timestamp<=exit_ts),'funding_rate']
        funding_return=float(rates.sum())/2
        basis_return=(spot_return+perp_return)/2; gross=basis_return+funding_return
        events.append({'symbol':symbol,'signal_timestamp':ts,'entry_timestamp':entry_ts,'exit_timestamp':exit_ts,
          'signal_basis':float(row.basis),'threshold':float(row.threshold),'entry_basis':float(entry.perp_open/entry.spot_open-1),
          'exit_basis':float(exit_.perp_open/exit_.spot_open-1),'bars_held':exit_i-entry_i,'timed_out':timed_out,
          'spot_return':spot_return,'perp_short_return':perp_return,'basis_return':basis_return,
          'funding_return':funding_return,'gross_return':gross})
        if timed_out: census['timeouts']+=1
        last_exit=exit_ts
    return events,census

def assign_folds(events):
    t=sorted(e['entry_timestamp'] for e in events)
    if not t:return
    b=[t[i*len(t)//4] for i in range(4)]
    for e in events:e['fold']=max(i for i,x in enumerate(b) if e['entry_timestamp']>=x)+1

def metrics(events,cost=PRIMARY_COST):
    v=np.asarray([e['gross_return']-cost for e in events])
    if not len(v):return {'n':0,'expectancy':None,'profit_factor':None,'win_rate':None,'max_drawdown':None}
    w,l=v[v>0],v[v<=0]; eq=v.cumsum(); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]
    return {'n':len(v),'expectancy':float(v.mean()),'profit_factor':float(w.sum()/-l.sum()) if len(l) and l.sum() else None,
      'win_rate':float((v>0).mean()),'max_drawdown':float((peak-eq).max(initial=0))}

def bootstrap(events,samples=10000):
    if not events:return [None,None]
    c={}
    for e in events:c.setdefault(e['entry_timestamp']//86400,[]).append(e['gross_return']-PRIMARY_COST)
    days=sorted(c); rng=np.random.default_rng(240024); out=np.empty(samples)
    for i in range(samples):
        chosen=rng.choice(days,len(days),replace=True); out[i]=np.mean([v for d in chosen for v in c[int(d)]])
    return [float(x) for x in np.quantile(out,[.025,.975])]

def collect(spot_dir,perp_dir,funding_dir,start,end):
    events=[]; census={}
    for s in SYMBOLS:
        panel=aligned_basis(spot_dir/f'{s}.csv.gz',perp_dir/f'{s}.csv'); funding=load_funding(funding_dir/f'{s}.csv')
        selected,counts=symbol_events(s,panel,funding,start,end); events+=selected; census[s]=counts
    assign_folds(events); return events,census

def summary(events):
    years=sorted({pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year for e in events})
    return {'overall':metrics(events),'clustered_bootstrap_95_ci':bootstrap(events),
      'by_fold':{f'F{i}':metrics([e for e in events if e['fold']==i]) for i in range(1,5)},
      'by_symbol':{s:metrics([e for e in events if e['symbol']==s]) for s in SYMBOLS},
      'by_year':{str(y):metrics([e for e in events if pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year==y]) for y in years},
      'cost_sensitivity':{f'{c:.4f}':metrics(events,c) for c in COSTS},
      'timeout_share':sum(e['timed_out'] for e in events)/len(events) if events else None,
      'mean_signal_basis':float(np.mean([e['signal_basis'] for e in events])) if events else None,
      'mean_basis_return':float(np.mean([e['basis_return'] for e in events])) if events else None,
      'mean_funding_return':float(np.mean([e['funding_return'] for e in events])) if events else None}

def build_report(spot_dir:Path,perp_dir:Path,funding_dir:Path)->dict[str,Any]:
    pe,pc=collect(spot_dir,perp_dir,funding_dir,PRIMARY_START,PRIMARY_END); re,rc=collect(spot_dir,perp_dir,funding_dir,REVERSE_START,REVERSE_END)
    p,r=summary(pe),summary(re); positive={s:sum(max(0,e['gross_return']-PRIMARY_COST) for e in pe if e['symbol']==s) for s in SYMBOLS}
    total=sum(positive.values()); concentration=max(positive.values(),default=0)/total if total else None
    checks={'primary_n':p['overall']['n']>=150,'primary_positive':p['overall']['expectancy'] is not None and p['overall']['expectancy']>0,
      'primary_pf':p['overall']['profit_factor'] is not None and p['overall']['profit_factor']>1,
      'bootstrap':p['clustered_bootstrap_95_ci'][0] is not None and p['clustered_bootstrap_95_ci'][0]>0,
      'folds':sum(v['n']>=20 and v['expectancy']>0 for v in p['by_fold'].values())>=3,
      'symbols':sum(v['n']>=20 and v['expectancy']>0 for v in p['by_symbol'].values())>=3,
      'concentration':concentration is not None and concentration<=.45,
      'reverse':r['overall']['n']>=50 and r['overall']['expectancy']>0 and r['overall']['profit_factor']>1,
      'timeout':p['timeout_share'] is not None and p['timeout_share']<=.5,
      'cost_003':p['cost_sensitivity']['0.0030']['expectancy'] is not None and p['cost_sensitivity']['0.0030']['expectancy']>0}
    return {'candidate':'C-24','protocol':'edge-candidate-register-v23','primary_census':pc,'reverse_census':rc,
      'primary':p,'reverse':r,'max_positive_pnl_symbol_concentration':concentration,
      'gate':{'checks':checks,'verdict':'KEEP_FOR_PROSPECTIVE_VALIDATION' if all(checks.values()) else 'REJECT'}}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--spot-dir',default='data/research/spot_15m/normalized'); p.add_argument('--perp-dir',default='data/research/c06/binance_futures_15m'); p.add_argument('--funding-dir',default='data/research/c16/funding'); p.add_argument('--output',default='docs/reports/edge_candidate_c24.json'); a=p.parse_args()
    report=build_report(Path(a.spot_dir),Path(a.perp_dir),Path(a.funding_dir)); rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False); target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(rendered+'\n'); print(rendered)
if __name__=='__main__':main()
