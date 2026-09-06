#!/usr/bin/env python3
"""Evaluate preregistered C-31 Spot-led perpetual underreaction."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

SYMBOLS=("BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","SOLUSDT")
LOOKBACK=4320;SHOCK_FLOOR=.005;RESPONSE_MAX=.50;HOLD_BARS=16;PRIMARY_COST=.003;COSTS=(.002,.003,.005)
PRIMARY_START,PRIMARY_END=1704067200,1788134400;REVERSE_START,REVERSE_END=1672531200,1704067200
SPOT_HASH={"BTCUSDT":"2b58717c3f464e84ab531db07f4263b4c83b52c2f6b460a5445ec150f9c5dec3","ETHUSDT":"79e83e1947022c51126093ef72ab97f0e38fe3d40851fed8c3ad5a15afce75fa","BNBUSDT":"29294ff4fe8c7ee52b3e35f36e944735c7fed09fb5e3878f0720d7ae3352c4c8","XRPUSDT":"a87b83e107e7536fa4e68b280c27700da9bd3f6dbd8b96ca8e39aa104c817455","ADAUSDT":"f081b9da47ce30e2746a235d6a78ad7269ef7add8d6738eac49ac8b1af7c5452","SOLUSDT":"7ac0701eeb2b50ac30cd3575219ada620d567783a3cd10be98813f39869c9011"}
PERP_HASH={"BTCUSDT":"30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb","ETHUSDT":"d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843","BNBUSDT":"7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0","XRPUSDT":"89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57","ADAUSDT":"643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a","SOLUSDT":"e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382"}
FUNDING_HASH={"BTCUSDT":"2fe89ca06907e7953cb49c2db052e74158ea9319f50f0bd9dac08fb2a579c097","ETHUSDT":"b978d9a54809ad232583b9419ed2695647d0557bc58074112082fa1472057148","BNBUSDT":"7edf30b5a20f5572361ba7bc41ff89b02df8105a82ff24c1b32a5dc807bca08d","XRPUSDT":"2886be913f6678b660e827d481a2b60d426de6c8b406bcff3c282d3f275e74f9","ADAUSDT":"f27f351e603c0563d9c1e0ea6be10640a8bf38c4a1640383d914cd5aaaa79301","SOLUSDT":"be28b9621e6baf0d3b50365c73e59352996274f4097cae60fe4ffce2528c55a3"}
def verify(path,expected):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f"frozen source hash mismatch: {path}")
def load_price(path):return pd.read_csv(path,usecols=['timestamp','open','close']).sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')
def load_funding(path):return pd.read_csv(path).sort_values('timestamp').drop_duplicates('timestamp')
def causal_features(spot,perp):
    rows=[]
    for ts in sorted(set(spot.index)&set(perp.index)):
        ts=int(ts)
        if ts%3600:continue
        current=ts-900;prior=ts-4500
        if any(x not in spot.index or x not in perp.index for x in (current,prior)):continue
        sr=float(spot.loc[current,'close']/spot.loc[prior,'close']-1);pr=float(perp.loc[current,'close']/perp.loc[prior,'close']-1)
        rows.append({'decision_timestamp':ts,'spot_return':sr,'perp_return':pr,'response_ratio':abs(pr)/abs(sr) if sr else np.nan})
    f=pd.DataFrame(rows).set_index('decision_timestamp')
    f['shock_threshold']=f.spot_return.abs().shift(1).rolling(LOOKBACK,min_periods=LOOKBACK).quantile(.95)
    return f
def collect(symbol,features,perp,funding,start,end):
    events=[];last_exit=-1;c={k:0 for k in ('period_rows','warmup_rejected','shock_rejected','sign_rejected','response_rejected','missing_path','overlap_rejected','signals')}
    for ts,r in features.iterrows():
        ts=int(ts)
        if not start<=ts<end:continue
        c['period_rows']+=1
        if pd.isna(r.shock_threshold):c['warmup_rejected']+=1;continue
        if not (abs(r.spot_return)>r.shock_threshold and abs(r.spot_return)>SHOCK_FLOOR):c['shock_rejected']+=1;continue
        if not r.spot_return*r.perp_return>0:c['sign_rejected']+=1;continue
        if not r.response_ratio<=RESPONSE_MAX:c['response_rejected']+=1;continue
        c['signals']+=1;exit_ts=ts+HOLD_BARS*900
        if any(ts+i*900 not in perp.index for i in range(HOLD_BARS+1)):c['missing_path']+=1;continue
        if ts<last_exit:c['overlap_rejected']+=1;continue
        direction=1 if r.spot_return>0 else -1;side='LONG' if direction>0 else 'SHORT';entry=float(perp.loc[ts,'open']);exit_price=float(perp.loc[exit_ts,'open']);price_return=direction*(exit_price/entry-1)
        rates=funding.loc[(funding.timestamp>ts)&(funding.timestamp<=exit_ts),'funding_rate'].sum();funding_return=-direction*float(rates)
        events.append({'symbol':symbol,'side':side,'entry_timestamp':ts,'exit_timestamp':exit_ts,'spot_return':float(r.spot_return),'perp_return':float(r.perp_return),'response_ratio':float(r.response_ratio),'price_return':price_return,'funding_return':funding_return,'gross_return':price_return+funding_return});last_exit=exit_ts
    return events,c
def assign_folds(events):
    ts=sorted(e['entry_timestamp'] for e in events)
    if not ts:return []
    bounds=[ts[i*len(ts)//4] for i in range(4)]+[max(ts)+HOLD_BARS*900+1];kept=[]
    for e in events:
        i=max(i for i,b in enumerate(bounds[:-1]) if e['entry_timestamp']>=b)
        if e['exit_timestamp']<bounds[i+1]:e['fold']=i+1;kept.append(e)
    return kept
def metrics(events,cost=PRIMARY_COST):
    v=np.asarray([e['gross_return']-cost for e in events])
    if not len(v):return {'n':0,'expectancy':None,'profit_factor':None,'win_rate':None,'max_drawdown':None}
    w,l=v[v>0],v[v<=0];eq=v.cumsum();peak=np.maximum.accumulate(np.r_[0.,eq])[1:]
    return {'n':int(len(v)),'expectancy':float(v.mean()),'profit_factor':float(w.sum()/-l.sum()) if len(l) and l.sum() else None,'win_rate':float((v>0).mean()),'max_drawdown':float((peak-eq).max(initial=0))}
def bootstrap(events):
    if not events:return [None,None]
    clusters={}
    for e in events:clusters.setdefault(e['entry_timestamp'],[]).append(e['gross_return']-PRIMARY_COST)
    keys=sorted(clusters);rng=np.random.default_rng(310031);out=[]
    for _ in range(10000):
        chosen=rng.choice(keys,len(keys),replace=True);out.append(np.mean([v for k in chosen for v in clusters[int(k)]]))
    return [float(x) for x in np.quantile(out,[.025,.975])]
def summary(events):
    years=sorted({pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year for e in events})
    return {'overall':metrics(events),'clustered_bootstrap_95_ci':bootstrap(events),'by_fold':{f'F{i}':metrics([e for e in events if e.get('fold')==i]) for i in range(1,5)},'by_side':{s:metrics([e for e in events if e['side']==s]) for s in ('LONG','SHORT')},'by_symbol':{s:metrics([e for e in events if e['symbol']==s]) for s in SYMBOLS},'by_year':{str(y):metrics([e for e in events if pd.to_datetime(e['entry_timestamp'],unit='s',utc=True).year==y]) for y in years},'cost_sensitivity':{f'{cost:.3f}':metrics(events,cost) for cost in COSTS},'mean_response_ratio':float(np.mean([e['response_ratio'] for e in events])) if events else None,'mean_funding_return':float(np.mean([e['funding_return'] for e in events])) if events else None}
def build_report(spot_dir,perp_dir,funding_dir):
    pe=[];re=[];pc={};rc={}
    for s in SYMBOLS:
        sp=spot_dir/f'{s}.csv.gz';pp=perp_dir/f'{s}.csv';fp=funding_dir/f'{s}.csv'
        for path,digest in ((sp,SPOT_HASH[s]),(pp,PERP_HASH[s]),(fp,FUNDING_HASH[s])):verify(path,digest)
        spot=load_price(sp);perp=load_price(pp);funding=load_funding(fp);features=causal_features(spot,perp)
        selected,c=collect(s,features,perp,funding,PRIMARY_START,PRIMARY_END);pe+=selected;pc[s]=c
        selected,c=collect(s,features,perp,funding,REVERSE_START,REVERSE_END);re+=selected;rc[s]=c
    pe=assign_folds(pe);assign_folds(re);p=summary(pe);r=summary(re);positive={s:sum(max(0,e['gross_return']-PRIMARY_COST) for e in pe if e['symbol']==s) for s in SYMBOLS};total=sum(positive.values());conc=max(positive.values(),default=0)/total if total else None;o=p['overall']
    checks={'primary_n':o['n']>=300,'primary_positive':o['expectancy'] is not None and o['expectancy']>0,'primary_pf':o['profit_factor'] is not None and o['profit_factor']>1,'bootstrap':p['clustered_bootstrap_95_ci'][0] is not None and p['clustered_bootstrap_95_ci'][0]>0,'folds':sum(v['n']>=50 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_fold'].values())>=3,'sides':all(v['n']>=75 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_side'].values()),'symbols':sum(v['n']>=40 and v['expectancy'] is not None and v['expectancy']>0 for v in p['by_symbol'].values())>=4,'years':all(p['by_year'].get(str(y),{'n':0})['n']>=50 and p['by_year'][str(y)]['expectancy']>0 for y in (2024,2025,2026)),'concentration':conc is not None and conc<=.35,'reverse':r['overall']['n']>=150 and r['overall']['expectancy'] is not None and r['overall']['expectancy']>0 and r['overall']['profit_factor'] is not None and r['overall']['profit_factor']>1,'cost_005':p['cost_sensitivity']['0.005']['expectancy'] is not None and p['cost_sensitivity']['0.005']['expectancy']>0}
    return {'candidate':'C-31','protocol':'edge-candidate-register-v30','primary_census':pc,'reverse_census':rc,'primary':p,'reverse':r,'max_positive_pnl_symbol_concentration':conc,'gate':{'checks':checks,'verdict':'KEEP_FOR_PROSPECTIVE_VALIDATION' if all(checks.values()) else 'REJECT'}}
def main():
    p=argparse.ArgumentParser();p.add_argument('--spot-dir',default='data/research/spot_15m/normalized');p.add_argument('--perp-dir',default='data/research/c06/binance_futures_15m');p.add_argument('--funding-dir',default='data/research/c16/funding');p.add_argument('--output',default='docs/reports/edge_candidate_c31.json');a=p.parse_args();report=build_report(Path(a.spot_dir),Path(a.perp_dir),Path(a.funding_dir));rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False);target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rendered+'\n');print(rendered)
if __name__=='__main__':main()
