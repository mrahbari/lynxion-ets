import importlib.util
from pathlib import Path
import pandas as pd

def module():
    p=Path(__file__).resolve().parents[2]/'scripts'/'evaluate_taker_flow_continuation_c21.py'; s=importlib.util.spec_from_file_location('c21',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def fixtures(m,n=182):
    b=m._base(); decisions=[b.DECISION_SECONDS*i for i in range(2,n+2)]; price=pd.DataFrame({'open':100.,'close':100.},index=decisions)
    times=range(decisions[0]-b.DECISION_SECONDS,decisions[-1],b.BAR_SECONDS); flow=pd.DataFrame({'quote_volume':100.,'taker_buy_quote_volume':60.},index=times); return b,decisions,price,flow

def test_requires_all_sixteen_completed_bars():
    m=module(); b,decisions,price,flow=fixtures(m); flow=flow.drop(decisions[-1]-2*b.BAR_SECONDS)
    features=m.causal_features(price,flow)
    assert decisions[-1] not in features.index and (features['snapshot_timestamp']==features.index-b.BAR_SECONDS).all()

def test_score_is_symmetric_taker_quote_imbalance():
    m=module(); _,_,price,flow=fixtures(m,1); feature=m.causal_features(price,flow).iloc[0]
    assert abs(feature['imbalance']-.2)<1e-12

def test_threshold_excludes_current_window():
    m=module(); b,decisions,price,flow=fixtures(m); flow.loc[decisions[-1]-b.DECISION_SECONDS:decisions[-1]-b.BAR_SECONDS,'taker_buy_quote_volume']=100.
    features=m.causal_features(price,flow)
    assert abs(features.iloc[-1]['threshold']-.2)<1e-12
