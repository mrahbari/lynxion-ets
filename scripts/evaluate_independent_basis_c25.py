#!/usr/bin/env python3
"""Evaluate preregistered C-25 independent basis-convergence confirmation."""

import argparse
import importlib.util
import json
from pathlib import Path

SYMBOLS=("DOGEUSDT","LINKUSDT","LTCUSDT","DOTUSDT","AVAXUSDT")

def mechanics():
    path=Path(__file__).with_name('evaluate_delta_neutral_basis_c24.py')
    spec=importlib.util.spec_from_file_location('basis_c24_mechanics',path); module=importlib.util.module_from_spec(spec)
    assert spec.loader; spec.loader.exec_module(module); module.SYMBOLS=SYMBOLS; return module

def build_report(spot_dir:Path,perp_dir:Path,funding_dir:Path):
    module=mechanics(); report=module.build_report(spot_dir,perp_dir,funding_dir)
    report['candidate']='C-25'; report['protocol']='edge-candidate-register-v24'; return report

def main():
    p=argparse.ArgumentParser(); p.add_argument('--spot-dir',default='data/research/spot_15m_independent/normalized'); p.add_argument('--perp-dir',default='data/research/c22/taker_flow/normalized'); p.add_argument('--funding-dir',default='data/research/c17/funding'); p.add_argument('--output',default='docs/reports/edge_candidate_c25.json'); a=p.parse_args()
    report=build_report(Path(a.spot_dir),Path(a.perp_dir),Path(a.funding_dir)); rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False); target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(rendered+'\n'); print(rendered)
if __name__=='__main__':main()
