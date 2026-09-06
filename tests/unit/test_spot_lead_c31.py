import hashlib
import pandas as pd
import pytest
from scripts import evaluate_spot_lead_c31 as c
def prices():
    ts=list(range(0,25000,900));return pd.DataFrame({'timestamp':ts,'open':[100.]*len(ts),'close':[100.]*len(ts)}).set_index('timestamp')
def test_current_decision_prices_do_not_enter_features(monkeypatch):
    monkeypatch.setattr(c,'LOOKBACK',1);spot=prices();perp=prices();f=c.causal_features(spot,perp);ts=f.index[2];base=f.loc[ts].copy();spot.loc[ts,'close']=1000;perp.loc[ts,'close']=1;changed=c.causal_features(spot,perp);pd.testing.assert_series_equal(base,changed.loc[ts])
def test_threshold_excludes_current_spot_return(monkeypatch):
    monkeypatch.setattr(c,'LOOKBACK',1);spot=prices();perp=prices();f=c.causal_features(spot,perp);ts=f.index[2];base=f.loc[ts,'shock_threshold'];spot.loc[ts-900,'close']=110;changed=c.causal_features(spot,perp);assert changed.loc[ts,'shock_threshold']==base
def test_long_funding_boundary_and_path(monkeypatch):
    monkeypatch.setattr(c,'HOLD_BARS',1);perp=prices();features=pd.DataFrame([{'spot_return':.02,'perp_return':.005,'response_ratio':.25,'shock_threshold':.01}],index=[3600]);funding=pd.DataFrame({'timestamp':[3600,4500,5400],'funding_rate':[.1,.02,.04]});events,_=c.collect('BTCUSDT',features,perp,funding,0,99999);assert events[0]['side']=='LONG';assert events[0]['funding_return']==pytest.approx(-.02)
def test_sign_and_response_gates_are_strict(monkeypatch):
    monkeypatch.setattr(c,'HOLD_BARS',1);perp=prices();funding=pd.DataFrame({'timestamp':[],'funding_rate':[]});base={'spot_return':.02,'perp_return':.005,'response_ratio':.25,'shock_threshold':.01}
    for changes in ({'perp_return':-.005},{'response_ratio':.50001}):
        features=pd.DataFrame([{**base,**changes}],index=[3600]);events,_=c.collect('BTCUSDT',features,perp,funding,0,99999);assert events==[]
def test_fold_crossing_is_excluded(monkeypatch):
    monkeypatch.setattr(c,'HOLD_BARS',1);events=[{'entry_timestamp':0,'exit_timestamp':900},{'entry_timestamp':900,'exit_timestamp':1800},{'entry_timestamp':1800,'exit_timestamp':2700},{'entry_timestamp':2700,'exit_timestamp':3600}]
    assert len(c.assign_folds(events))<len(events)
def test_hash_and_empty_fail_closed(tmp_path):
    p=tmp_path/'x';p.write_bytes(b'a');digest=hashlib.sha256(b'a').hexdigest();c.verify(p,digest);p.write_bytes(b'b')
    with pytest.raises(ValueError):c.verify(p,digest)
    assert c.metrics([])['expectancy'] is None and c.bootstrap([])==[None,None]
