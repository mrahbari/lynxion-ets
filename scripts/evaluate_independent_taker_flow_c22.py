#!/usr/bin/env python3
"""Evaluate preregistered C-22 independent taker-flow confirmation."""
import argparse,importlib.util,json
from pathlib import Path

_path=Path(__file__).with_name('evaluate_taker_flow_continuation_c21.py')
_spec=importlib.util.spec_from_file_location('c21_base',_path); c21=importlib.util.module_from_spec(_spec)
assert _spec.loader; _spec.loader.exec_module(c21)

SYMBOLS=("DOGEUSDT","LINKUSDT","LTCUSDT","DOTUSDT","AVAXUSDT")

def build_report(price_dir,flow_dir,funding_dir):
    base=c21._base(); base.SYMBOLS=SYMBOLS; base.MAX_CONCENTRATION=.35
    base.load_book=c21.load_flow; base.causal_features=c21.causal_features
    report=base.build_report(price_dir,flow_dir,funding_dir); report['candidate']='C-22'; report['protocol']='edge-candidate-register-v21'; return report

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--price-dir',default='data/research/c15/binance_futures_15m'); p.add_argument('--flow-dir',default='data/research/c22/taker_flow/normalized'); p.add_argument('--funding-dir',default='data/research/c17/funding'); p.add_argument('--output',default='docs/reports/edge_candidate_c22_holdout.json'); a=p.parse_args()
    report=build_report(Path(a.price_dir),Path(a.flow_dir),Path(a.funding_dir)); text=json.dumps(report,indent=2,sort_keys=True,allow_nan=False); target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text+'\n'); print(text)
