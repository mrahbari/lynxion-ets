import importlib.util
from pathlib import Path

def module():
 p=Path(__file__).resolve().parents[2]/'scripts'/'census_binance_aggtrades.py';s=importlib.util.spec_from_file_location('census',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_classify_requires_zip_and_checksum():
 m=module();s='BTCUSDT';base=f'data/futures/um/daily/aggTrades/{s}/{s}-aggTrades-2023-01-01.zip';by,complete,missing,_=m.classify(s,[{'key':base,'size':10},{'key':base+'.CHECKSUM','size':2}])
 assert complete==['2023-01-01'] and '2023-01-02' in missing and by['2023-01-01']['zip']['size']==10

def test_dates_outside_frozen_range_are_ignored():
 m=module();s='ETHUSDT';key=f'data/futures/um/daily/aggTrades/{s}/{s}-aggTrades-2022-12-31.zip';by,complete,_,unexpected=m.classify(s,[{'key':key,'size':1}])
 assert by=={} and complete==[] and unexpected==[]
