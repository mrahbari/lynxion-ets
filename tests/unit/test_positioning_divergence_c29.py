import hashlib
import pandas as pd
import pytest
from scripts import evaluate_positioning_divergence_c29 as c

def fixture(monkeypatch):
    monkeypatch.setattr(c,'WARMUP',2);monkeypatch.setattr(c,'HOLD',900)
    price=pd.DataFrame({'timestamp':range(0,72001,900),'open':[100.]*81}).set_index('timestamp')
    rows=[]
    for ts in range(c.DECISION,72001,c.DECISION):rows.append({'timestamp':ts-300,'count_long_short_ratio':2.,'sum_toptrader_long_short_ratio':.5})
    metrics=pd.DataFrame(rows).set_index('timestamp');funding=pd.DataFrame({'timestamp':[c.DECISION,c.DECISION+900],'funding_rate':[.1,.02]})
    return price,metrics,funding
def test_features_use_exact_predecision_metric_and_prior_threshold(monkeypatch):
    price,m,_=fixture(monkeypatch);f=c.causal_features(price,m);ts=f.index[2];base=f.loc[ts].copy();m.loc[ts-300,'count_long_short_ratio']=20;changed=c.causal_features(price,m)
    assert changed.loc[ts,'crowd_threshold']==base.crowd_threshold
    assert changed.loc[ts,'crowd']!=base.crowd
def test_trade_follows_top_and_funding_boundary(monkeypatch):
    price,m,_=fixture(monkeypatch);features=c.causal_features(price,m);ts=features.dropna().index[0];features.loc[ts,['crowd','top','crowd_threshold','divergence_threshold','divergence']]=[1,-1,.1,.1,2]
    funding=pd.DataFrame({'timestamp':[ts,ts+900,ts+1800],'funding_rate':[.1,.02,.04]})
    events,_=c.collect('BTCUSDT',features,price,funding,0,999999);assert events[0]['side']=='SHORT';assert events[0]['funding_return']==pytest.approx(.02)
def test_same_side_is_no_signal(monkeypatch):
    price,m,funding=fixture(monkeypatch);features=c.causal_features(price,m);ts=features.dropna().index[0];features.loc[ts,['crowd','top','crowd_threshold','divergence_threshold','divergence']]=[1,1,.1,.1,2]
    events,_=c.collect('BTCUSDT',features,price,funding,0,999999);assert events==[]
def test_empty_outputs_fail_closed():
    assert c.metrics([])['expectancy'] is None;assert c.bootstrap([])==[None,None]
def test_hash_guard_fails_closed(tmp_path):
    path=tmp_path/'source';path.write_bytes(b'frozen');digest=hashlib.sha256(b'frozen').hexdigest();c.verify(path,digest);path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='frozen source hash mismatch'):c.verify(path,digest)
