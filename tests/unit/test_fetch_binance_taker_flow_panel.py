import importlib.util,io,zipfile
from pathlib import Path

def module():
    p=Path(__file__).resolve().parents[2]/'scripts'/'fetch_binance_taker_flow_panel.py'; s=importlib.util.spec_from_file_location('flow',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def zipped(rows):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z: z.writestr('x.csv','\n'.join(','.join(map(str,r)) for r in rows)+'\n')
    return b.getvalue()

def row(t=0,quote=100,taker=40): return [t,100,110,90,105,1,t+899999,quote,10,1,taker,0]

def test_parser_accepts_valid_flow(tmp_path):
    m=module(); p=tmp_path/'x.zip'; p.write_bytes(zipped([row()])); rows,c=m.parse_archive(p)
    assert len(rows)==1 and c['flow_violations']==0

def test_parser_rejects_taker_above_total(tmp_path):
    m=module(); p=tmp_path/'x.zip'; p.write_bytes(zipped([row(quote=10,taker=11)])); rows,c=m.parse_archive(p)
    assert rows==[] and c['flow_violations']==1

def test_parser_rejects_bad_ohlc(tmp_path):
    m=module(); bad=row(); bad[2]=95; p=tmp_path/'x.zip'; p.write_bytes(zipped([bad])); rows,c=m.parse_archive(p)
    assert rows==[] and c['ohlc_violations']==1

def test_parser_censuses_zero_volume_partial_source_candle(tmp_path):
    m=module(); partial=row(); partial[6]=500000; partial[7]=0; partial[8]=0; partial[10]=0; p=tmp_path/'x.zip'; p.write_bytes(zipped([partial])); rows,c=m.parse_archive(p)
    assert rows==[] and c['partial_source_candles']==1 and c['timestamp_violations']==0

def test_build_accepts_custom_universe_and_task(tmp_path,monkeypatch):
    m=module(); markets=[]; monkeypatch.setattr(m,'list_archives',lambda *a,**kw:(markets.append(kw['market']) or [])); monkeypatch.setattr(m,'normalize',lambda s,*a:{'unique_rows':120000,'missing_intervals':0,'conflicting_duplicates':0,'schema_violations':0,'numeric_violations':0,'timestamp_violations':0,'partial_source_candles':0,'ohlc_violations':0,'flow_violations':0})
    report=m.build(tmp_path,1,('DOGEUSDT',),'TASK-X','spot')
    assert report['task']=='TASK-X' and list(report['symbols'])==['DOGEUSDT']
    assert report['market']=='spot' and markets==['spot']
