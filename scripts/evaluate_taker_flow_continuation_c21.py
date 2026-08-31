#!/usr/bin/env python3
"""Evaluate preregistered C-21 aggressive taker-flow continuation."""

from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

def _base():
    p=Path(__file__).with_name('evaluate_bookdepth_imbalance_c18.py')
    s=importlib.util.spec_from_file_location('c18_base',p); m=importlib.util.module_from_spec(s)
    assert s.loader; s.loader.exec_module(m); return m

def load_flow(path: Path) -> pd.DataFrame:
    cols=['timestamp','quote_volume','taker_buy_quote_volume']; f=pd.read_csv(path,usecols=cols)
    f[cols]=f[cols].apply(pd.to_numeric,errors='coerce')
    return f.dropna().sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')

def causal_features(price: pd.DataFrame, flow: pd.DataFrame) -> pd.DataFrame:
    base=_base(); index=set(flow.index.astype(int)); rows=[]
    for raw in price.index:
        t=int(raw)
        if t%base.DECISION_SECONDS: continue
        window=[t-base.DECISION_SECONDS+i*base.BAR_SECONDS for i in range(16)]
        if any(ts not in index for ts in window): continue
        selected=flow.loc[window]; total=float(selected['quote_volume'].sum()); buy=float(selected['taker_buy_quote_volume'].sum())
        if not np.isfinite(total) or not np.isfinite(buy) or total<=0 or buy<0 or buy>total: continue
        rows.append({'decision_timestamp':t,'snapshot_timestamp':t-base.BAR_SECONDS,
                     'book_age_seconds':base.BAR_SECONDS,'imbalance':(2*buy-total)/total,
                     'window_quote_volume':total})
    cols=['snapshot_timestamp','book_age_seconds','imbalance','window_quote_volume','threshold']
    if not rows: return pd.DataFrame(columns=cols).rename_axis('decision_timestamp')
    f=pd.DataFrame(rows).set_index('decision_timestamp')
    f['threshold']=f['imbalance'].abs().shift(1).rolling(base.WARMUP,min_periods=base.WARMUP).quantile(.90)
    return f

def build_report(price_dir:Path,flow_dir:Path,funding_dir:Path):
    base=_base(); base.load_book=load_flow; base.causal_features=causal_features
    report=base.build_report(price_dir,flow_dir,funding_dir); report['candidate']='C-21'; report['protocol']='edge-candidate-register-v20'; return report

def main():
    p=argparse.ArgumentParser(); p.add_argument('--price-dir',default='data/research/c06/binance_futures_15m'); p.add_argument('--flow-dir',default='data/research/taker_flow/normalized'); p.add_argument('--funding-dir',default='data/research/c16/funding'); p.add_argument('--output',default='docs/reports/edge_candidate_c21_holdout.json'); a=p.parse_args()
    report=build_report(Path(a.price_dir),Path(a.flow_dir),Path(a.funding_dir)); rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False)
    target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(rendered+'\n'); print(rendered)

if __name__=='__main__': main()
