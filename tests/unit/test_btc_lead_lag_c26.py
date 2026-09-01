import importlib.util
from pathlib import Path
import pandas as pd
import pytest

def module():
 p=Path(__file__).resolve().parents[2]/'scripts'/'evaluate_btc_lead_lag_c26.py';s=importlib.util.spec_from_file_location('c26',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_completed_hour_requires_four_contiguous_bars():
 m=module();f=pd.DataFrame({'timestamp':[0,900,1800,2700,3600,5400,6300],'open':[100]*7,'close':[101]*7}).set_index('timestamp');h=m.completed_hours(f)
 assert h.timestamp.tolist()==[3600]

def test_causal_threshold_excludes_current():
 m=module();n=(m.LOOKBACK+2)*4;f=pd.DataFrame({'timestamp':[i*900 for i in range(n)],'open':[100.]*n,'close':[100.]*n}).set_index('timestamp');a=m.btc_context(f);f.loc[(m.LOOKBACK*4+3)*900,'close']=200;b=m.btc_context(f)
 assert a.loc[m.LOOKBACK,'threshold']==b.loc[m.LOOKBACK,'threshold']

def fixture():
 m=module();btc=pd.DataFrame({'timestamp':[3600],'return':[.02],'threshold':[.01]});alt=pd.DataFrame({'timestamp':[3600],'return':[.004]});idx=[3600+i*900 for i in range(17)];price=pd.DataFrame({'open':[100]+[101]*16,'close':[100]*17},index=idx);fund=pd.DataFrame({'timestamp':[7200],'funding_rate':[.001]});return m,btc,alt,price,fund

def test_response_next_open_exit_and_long_funding():
 m,b,a,p,f=fixture();events,_=m.symbol_events('ETHUSDT',b,a,p,f,0,10**9);e=events[0]
 assert e['side']=='LONG' and e['entry_timestamp']==3600 and e['exit_timestamp']==18000
 assert e['funding_return']==pytest.approx(-.001) and e['response_ratio']==pytest.approx(.2)

def test_short_receives_funding():
 m,b,a,p,f=fixture();b['return']=-.02;a['return']=-.004;events,_=m.symbol_events('ETHUSDT',b,a,p,f,0,10**9)
 assert events[0]['side']=='SHORT' and events[0]['funding_return']==pytest.approx(.001)

def test_missing_path_overlap_and_cost():
 m,b,a,p,f=fixture();p=p.drop(7200);events,c=m.symbol_events('ETHUSDT',b,a,p,f,0,10**9)
 assert events==[] and c['missing_path']==1 and m.metrics([{'gross_return':.01}],.003)['expectancy']==pytest.approx(.007)
