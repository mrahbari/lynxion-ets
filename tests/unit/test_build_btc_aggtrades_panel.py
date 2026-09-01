import csv,importlib.util,io,zipfile
from pathlib import Path
import pytest

def module():
 p=Path(__file__).resolve().parents[2]/'scripts'/'build_btc_aggtrades_panel.py';s=importlib.util.spec_from_file_location('panel',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def archive(tmp_path,rows,header=True):
 m=module();b=io.StringIO();w=csv.writer(b)
 if header:w.writerow(m.HEADER)
 w.writerows(rows);p=tmp_path/'x.zip'
 with zipfile.ZipFile(p,'w') as z:z.writestr('x.csv',b.getvalue())
 return p

def test_parser_preserves_maker_side_semantics(tmp_path):
 m=module();p=archive(tmp_path,[[1,100,2,1,1,1_700_000_000_000,'true'],[2,100,1,2,2,1_700_000_001_000,'false']]);rows,c=m.parse_archive(p);r=rows[0]
 assert r['seller_quote_volume']==200 and r['buyer_quote_volume']==100
 assert r['signed_imbalance']==pytest.approx(-1/3) and c['raw_rows']==2

def test_parser_accepts_microseconds_and_computes_tail(tmp_path):
 m=module();p=archive(tmp_path,[[1,100,1,1,1,1_700_000_000_000_000,'false'],[2,100,10,2,2,1_700_000_001_000_000,'false']]);rows,_=m.parse_archive(p)
 assert rows[0]['timestamp']==1_699_999_200 and rows[0]['max_quote_size']==1000 and rows[0]['top_1pct_quote_share']==pytest.approx(10/11)

def test_parser_censuses_duplicate_and_invalid_side(tmp_path):
 m=module();p=archive(tmp_path,[[1,100,1,1,1,1000,'false'],[1,100,1,1,1,2000,'false'],[2,100,1,2,2,3000,'x']]);_,c=m.parse_archive(p)
 assert c['duplicate_ids']==1 and c['side_violations']==1

def test_finalizer_is_deterministic_and_reports_conflicts(tmp_path,monkeypatch):
 m=module();monkeypatch.setattr(m,'START','2024-01-01');monkeypatch.setattr(m,'END','2024-01-02');monkeypatch.setattr(m,'RESERVE',0)
 row={'timestamp':1704067200,'trade_count':1,'quote_volume':100,'buyer_quote_volume':100,'seller_quote_volume':0,'signed_imbalance':1,'max_quote_size':100,'mean_quote_size':100,'std_quote_size':0,'top_1pct_quote_share':1}
 m.write_daily(tmp_path/'daily'/'2024-01-01.csv.gz',[row]);changed=dict(row,quote_volume=200);m.write_daily(tmp_path/'daily'/'2024-01-02.csv.gz',[changed])
 checks={k:0 for k in ('schema_violations','numeric_violations','timestamp_violations','side_violations','id_time_violations','duplicate_ids')};manifest={'days':{'2024-01-01':{'checks':checks},'2024-01-02':{'checks':checks}}}
 out=m.finalize(tmp_path,manifest);first=out['normalized']['sha256'];out=m.finalize(tmp_path,manifest)
 assert out['normalized']['conflicting_duplicates']==1 and out['normalized']['sha256']==first and out['gate']['verdict']=='REJECT'
