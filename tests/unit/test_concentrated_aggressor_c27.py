import importlib.util
from pathlib import Path
import pandas as pd
import pytest

def module():
 p=Path(__file__).resolve().parents[2]/'scripts'/'evaluate_concentrated_aggressor_c27.py';s=importlib.util.spec_from_file_location('c27',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_causal_thresholds_exclude_current():
 m=module();n=m.LOOKBACK+2;f=pd.DataFrame({'timestamp':[i*900 for i in range(n)],'top_1pct_quote_share':[.1]*n,'signed_imbalance':[.1]*n});a=m.causal_features(f);f.loc[m.LOOKBACK,'top_1pct_quote_share']=.99;f.loc[m.LOOKBACK,'signed_imbalance']=.99;b=m.causal_features(f)
 assert a.loc[m.LOOKBACK,'share_threshold']==b.loc[m.LOOKBACK,'share_threshold']
 assert a.loc[m.LOOKBACK,'imbalance_threshold']==b.loc[m.LOOKBACK,'imbalance_threshold']

def fixture(imbalance=.5):
 m=module();f=pd.DataFrame({'timestamp':[0],'top_1pct_quote_share':[.8],'signed_imbalance':[imbalance],'share_threshold':[.5],'imbalance_threshold':[.2]});idx=[900+i*900 for i in range(17)];p=pd.DataFrame({'open':[100]+[101]*16},index=idx);fund=pd.DataFrame({'timestamp':[3600],'funding_rate':[.001]});return m,f,p,fund

def test_conjunction_reversal_next_open_exit_and_short_funding():
 m,f,p,fund=fixture();events,c=m.collect_events(f,p,fund,0,10**9);e=events[0]
 assert c['signals']==1 and e['side']=='SHORT' and e['entry_timestamp']==900 and e['exit_timestamp']==15300
 assert e['funding_return']==pytest.approx(.001)

def test_negative_imbalance_reverses_long_and_pays_funding():
 m,f,p,fund=fixture(-.5);events,_=m.collect_events(f,p,fund,0,10**9)
 assert events[0]['side']=='LONG' and events[0]['funding_return']==pytest.approx(-.001)

def test_signal_requires_both_filters():
 m,f,p,fund=fixture();f['top_1pct_quote_share']=.4;events,c=m.collect_events(f,p,fund,0,10**9)
 assert events==[] and c['concentration_rejected']==1
 f['top_1pct_quote_share']=.8;f['signed_imbalance']=.25;events,c=m.collect_events(f,p,fund,0,10**9)
 assert events==[] and c['imbalance_rejected']==1

def test_missing_path_overlap_and_cost():
 m,f,p,fund=fixture();f2=pd.concat([f,f.assign(timestamp=1800)],ignore_index=True);p=p.drop(4500);events,c=m.collect_events(f2,p,fund,0,10**9)
 assert events==[] and c['missing_path']==2
 assert m.metrics([{'gross_return':.01}],.003)['expectancy']==pytest.approx(.007)
