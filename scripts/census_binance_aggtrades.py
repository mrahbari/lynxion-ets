#!/usr/bin/env python3
"""Listing-only feasibility census for official Binance Futures aggregate trades."""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,xml.etree.ElementTree as ET,zipfile
from datetime import date,timedelta
from io import BytesIO
from pathlib import Path
import requests

S3='https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'; DATA='https://data.binance.vision/'
SYMBOLS=('BTCUSDT','ETHUSDT'); START=date(2023,1,1); END=date(2026,8,29); RESERVE=20*1024**3

def list_objects(symbol,get=requests.get):
    prefix=f'data/futures/um/daily/aggTrades/{symbol}/'; token=None; out=[]
    while True:
        params={'list-type':'2','prefix':prefix,'max-keys':1000}
        if token:params['continuation-token']=token
        r=get(S3,params=params,timeout=30);r.raise_for_status();root=ET.fromstring(r.content);ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
        for item in root.findall('s:Contents',ns):out.append({'key':item.findtext('s:Key',namespaces=ns),'size':int(item.findtext('s:Size',namespaces=ns))})
        token=root.findtext('s:NextContinuationToken',namespaces=ns)
        if not token:break
    return out

def expected_dates():
    n=(END-START).days+1;return {(START+timedelta(days=i)).isoformat() for i in range(n)}

def classify(symbol,objects):
    pattern=re.compile(rf'/{symbol}-aggTrades-(\d{{4}}-\d{{2}}-\d{{2}})\.zip(\.CHECKSUM)?$'); by={}
    for obj in objects:
        m=pattern.search(obj['key'])
        if not m or not START.isoformat()<=m.group(1)<=END.isoformat():continue
        by.setdefault(m.group(1),{})['checksum' if m.group(2) else 'zip']=obj
    expected=expected_dates(); complete=sorted(d for d,v in by.items() if 'zip'in v and 'checksum'in v)
    return by,complete,sorted(expected-set(complete)),sorted(set(by)-expected)

def sample_archive(zip_obj,checksum_obj,get=requests.get):
    z=get(DATA+zip_obj['key'],timeout=60);z.raise_for_status();c=get(DATA+checksum_obj['key'],timeout=30);c.raise_for_status();expected=c.text.strip().split()[0]
    digest=hashlib.sha256(z.content).hexdigest()
    if digest!=expected:raise ValueError('checksum mismatch')
    with zipfile.ZipFile(BytesIO(z.content)) as archive:
        members=[n for n in archive.namelist() if n.endswith('.csv')]
        if len(members)!=1:raise ValueError('expected one CSV')
        raw=archive.read(members[0]);lines=raw.splitlines();header=lines[0].decode().split(',')
    return {'key':zip_obj['key'],'compressed_bytes':len(z.content),'uncompressed_bytes':len(raw),'rows_including_header':len(lines),'header':header,'sha256':digest}

def build_report(get=requests.get,disk_usage=shutil.disk_usage):
    symbols={};samples=[]
    for symbol in SYMBOLS:
        by,complete,missing,unexpected=classify(symbol,list_objects(symbol,get));sample=sample_archive(by[complete[0]]['zip'],by[complete[0]]['checksum'],get);samples.append(sample)
        symbols[symbol]={'complete_dates':len(complete),'first_date':complete[0] if complete else None,'last_date':complete[-1] if complete else None,'missing_dates':missing,'unexpected_dates':unexpected,'compressed_zip_bytes':sum(by[d]['zip']['size'] for d in complete),'sample':sample}
    compressed=sum(v['compressed_zip_bytes'] for v in symbols.values());ratio=max(s['uncompressed_bytes']/s['compressed_bytes'] for s in samples);expanded=int(compressed*ratio*1.25);normalized=2*len(expected_dates())*96*64
    free=disk_usage('.').free;streaming_peak=compressed+max(s['uncompressed_bytes'] for s in samples)*2+normalized
    checks={'complete_coverage':all(not v['missing_dates'] for v in symbols.values()),'sample_schema':all(s['header']==['agg_trade_id','price','quantity','first_trade_id','last_trade_id','transact_time','is_buyer_maker'] for s in samples),'streaming_storage_with_reserve':streaming_peak+RESERVE<=free}
    return {'task':'TASK-0127','source':DATA,'symbols':symbols,'storage':{'free_bytes':free,'safety_reserve_bytes':RESERVE,'compressed_corpus_bytes':compressed,'projected_full_expanded_bytes':expanded,'projected_normalized_bytes':normalized,'projected_streaming_peak_bytes':streaming_peak},'gate':{'checks':checks,'verdict':'GO' if all(checks.values()) else 'NO_GO'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='docs/reports/aggtrades_feasibility.json');a=p.parse_args();report=build_report();rendered=json.dumps(report,indent=2,sort_keys=True);target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rendered+'\n');print(rendered)
if __name__=='__main__':main()
