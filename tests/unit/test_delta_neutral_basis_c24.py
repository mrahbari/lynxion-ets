import importlib.util
from pathlib import Path
import pandas as pd
import pytest

def module():
    p=Path(__file__).resolve().parents[2]/'scripts'/'evaluate_delta_neutral_basis_c24.py'; s=importlib.util.spec_from_file_location('c24',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def fixture():
    m=module(); n=m.LOOKBACK+110; ts=[i*900 for i in range(n)]; spot=pd.DataFrame({'timestamp':ts,'spot_open':[100.]*n,'spot_close':[100.]*n,'perp_open':[100.]*n,'perp_close':[100.]*n}); spot['basis']=0.; spot['threshold']=0.001
    i=m.LOOKBACK; spot.loc[i,['basis','perp_close']]=[.01,101.]; spot.loc[i+1,['basis','perp_open','perp_close']]=[.01,101.,101.]; spot.loc[i+2,'basis']=0.; spot.loc[i+3,'perp_open']=100.
    funding=pd.DataFrame({'timestamp':[ts[i+2]],'funding_rate':[.002]}); return m,spot,funding,i

def test_causal_threshold_excludes_current(tmp_path):
    m=module(); n=m.LOOKBACK+2; s=pd.DataFrame({'timestamp':[i*900 for i in range(n)],'open':[100.]*n,'close':[100.]*n}); p=pd.DataFrame({'timestamp':s.timestamp,'open':[100.]*n,'close':[100.]*n}); p.loc[m.LOOKBACK,'close']=200
    a=tmp_path/'s.csv'; b=tmp_path/'p.csv'; s.to_csv(a,index=False); p.to_csv(b,index=False); f=m.aligned_basis(a,b)
    assert f.loc[m.LOOKBACK,'threshold']==pytest.approx(0)

def test_next_open_convergence_exit_and_leg_math():
    m,panel,funding,i=fixture(); trades,_=m.symbol_events('BTCUSDT',panel,funding,0,10**9); t=trades[0]
    assert t['entry_timestamp']==panel.loc[i+1,'timestamp'] and t['exit_timestamp']==panel.loc[i+3,'timestamp']
    assert t['perp_short_return']==pytest.approx((101-100)/101) and t['funding_return']==pytest.approx(.001)

def test_timeout_is_96_bars():
    m,panel,funding,i=fixture(); panel.loc[i+1:i+m.TIMEOUT,'basis']=.01; trades,c=m.symbol_events('BTCUSDT',panel,funding,0,10**9)
    assert trades[0]['timed_out'] and trades[0]['bars_held']==96 and c['timeouts']==1

def test_missing_next_open_fails_closed():
    m,panel,funding,i=fixture(); panel.loc[i+1,'timestamp']+=1; trades,c=m.symbol_events('BTCUSDT',panel,funding,0,10**9)
    assert trades==[] and c['missing_next_open']>=1

def test_overlap_and_cost():
    m,panel,funding,i=fixture(); panel.loc[i+1,'basis']=.02; panel.loc[i+1,'perp_close']=102; trades,c=m.symbol_events('BTCUSDT',panel,funding,0,10**9)
    assert c['overlap_rejected']==1 and m.metrics([{'gross_return':.01}],.002)['expectancy']==pytest.approx(.008)
