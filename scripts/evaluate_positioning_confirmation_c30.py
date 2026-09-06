#!/usr/bin/env python3
"""Evaluate preregistered C-30 on the disjoint five-symbol universe."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from scripts import evaluate_positioning_divergence_c29 as evaluator

SYMBOLS=("AVAXUSDT","DOGEUSDT","DOTUSDT","LINKUSDT","LTCUSDT")
CANDIDATE="C-30";PROTOCOL="edge-candidate-register-v29";BOOTSTRAP_SEED=300030
PRIMARY_PRICE_HASH={"AVAXUSDT":"1e78a738069199357586350b5653c4cef75150666416e00cd7254167cf6e1034","DOGEUSDT":"f3170d93bd2f2e08c8b011d286220ee97de09e465f044fdd764a837fe461d4fd","DOTUSDT":"fe919ae304f7eab4e0daa224efc657d39af45ca3dd0a8a6b955bd6000cea315c","LINKUSDT":"5828638c2ed38d1c23addd106551efbfadd3f5bbb7c912699b910c25e72b8d62","LTCUSDT":"fd6922e8488c1b37b1f666418f681b9edc8da6062e7cbf0b32451b01c68c28e8"}
REVERSE_PRICE_HASH={"AVAXUSDT":"30820954f5937d01a6bef8f8ee28ea740b9d633430412a2abb53b1c97f0a8787","DOGEUSDT":"bc89f4f41f39dbeb0a5cb9f1eb263e7c93a287acaf64d791ff9fdd7b86b0b013","DOTUSDT":"5c3e4ef533a989d97f48914cdb79c3f49ae5ab12f88b2ff034c9956d79e63d1c","LINKUSDT":"c4bbc2b19187f216987ff27af600330d05a01be5e1a323568caba2dac1692ae1","LTCUSDT":"543a4c6fbc94450f8f77f0c5b8a090a33c12363e317bd0eec3d4f513972be7f9"}
METRIC_HASH={"AVAXUSDT":"4594a6b040654047d1b5d7a0628b4366d9081746e7ac0d17555030d2c4053d71","DOGEUSDT":"5d2982ad761a01504237b2b3129b00209a21f1d2eeadecc3e27d4863c5032100","DOTUSDT":"21e65f486869c6010c882fbcd620a1bc8564c531f97cd988407ed598123e8aa8","LINKUSDT":"f46dddfa3c910748755902f2950efd37d969f2cba57b558e75676b7c3ac32982","LTCUSDT":"682458983b6c6a133241b8189b3f0b250f3cd4757eb680c43d7d510068f4a57d"}
FUNDING_HASH={"AVAXUSDT":"2aacfffc05219a440ba7e87766eea26af692a7399ef10f5be3b5d1d640ae591f","DOGEUSDT":"00132b8cc6ad3ff733ae382a385569e080fd016b62f65f7a8cbb4689eacd341b","DOTUSDT":"6a6ff1fed52b61201f1d63463d902a2e690338667ebfd57f1902dc5668702bb8","LINKUSDT":"c2dcd51c6c1b7b5e744d4de7b95a231cdbb200d05718a40d85c832b7d69d86a9","LTCUSDT":"b36acf3bee53ff5e5a4017503b80cd5ec7d8b0d1bb9d496b5809fe2d19e8bc9b"}

def build_report(primary,reverse,metrics,funding):
    names=('SYMBOLS','CANDIDATE','PROTOCOL','BOOTSTRAP_SEED','PRIMARY_PRICE_HASH','REVERSE_PRICE_HASH','METRIC_HASH','FUNDING_HASH')
    old={name:getattr(evaluator,name) for name in names}
    try:
        for name in names:setattr(evaluator,name,globals()[name])
        return evaluator.build_report(primary,reverse,metrics,funding)
    finally:
        for name,value in old.items():setattr(evaluator,name,value)

def main():
    p=argparse.ArgumentParser();p.add_argument('--primary-price-dir',default='data/research/c15/binance_futures_15m');p.add_argument('--reverse-price-dir',default='data/research/c17/reverse_price');p.add_argument('--metric-dir',default='data/research/c17/oi_metrics/normalized');p.add_argument('--funding-dir',default='data/research/c17/funding');p.add_argument('--output',default='docs/reports/edge_candidate_c30.json');a=p.parse_args()
    report=build_report(Path(a.primary_price_dir),Path(a.reverse_price_dir),Path(a.metric_dir),Path(a.funding_dir));rendered=json.dumps(report,indent=2,sort_keys=True,allow_nan=False);target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rendered+'\n');print(rendered)
if __name__=='__main__':main()
