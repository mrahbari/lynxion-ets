#!/usr/bin/env python3
"""Build bounded checksum-verified BTCUSDT aggregate-trade 15m panel for TASK-0128."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,importlib.util,io,itertools,json,math,shutil,zipfile
from pathlib import Path
import numpy as np
import requests

START='2024-01-01';END='2026-08-29';SYMBOL='BTCUSDT';RESERVE=20*1024**3
HEADER=['agg_trade_id','price','quantity','first_trade_id','last_trade_id','transact_time','is_buyer_maker']

def census_module():
 p=Path(__file__).with_name('census_binance_aggtrades.py');s=importlib.util.spec_from_file_location('agg_census',p);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m

def normalize_timestamp(value):
 t=int(value)
 if t>=10**15:t//=1000
 if t>=10**12:t//=1000
 return t

def parse_archive(path):
 checks={'raw_rows':0,'schema_violations':0,'numeric_violations':0,'timestamp_violations':0,'side_violations':0,'id_time_violations':0,'duplicate_ids':0};buckets={};seen=set();last_id=-1;last_ts=-1
 with zipfile.ZipFile(path) as z:
  members=[n for n in z.namelist() if n.endswith('.csv')]
  if len(members)!=1:raise ValueError('expected one CSV')
  with z.open(members[0]) as raw:
   reader=csv.reader(io.TextIOWrapper(raw,encoding='utf-8',newline=''));first=next(reader,None)
   rows=reader if first==HEADER else itertools.chain(([first] if first else []),reader)
   for row in rows:
    checks['raw_rows']+=1
    if len(row)!=7:checks['schema_violations']+=1;continue
    try:
     aid=int(row[0]);price=float(row[1]);qty=float(row[2]);ts=normalize_timestamp(row[5])
    except (ValueError,TypeError,OverflowError):checks['numeric_violations']+=1;continue
    if not all(math.isfinite(x) and x>0 for x in (price,qty)):checks['numeric_violations']+=1;continue
    if ts<=0:checks['timestamp_violations']+=1;continue
    side=row[6].strip().lower()
    if side not in ('true','false'):checks['side_violations']+=1;continue
    if aid in seen:checks['duplicate_ids']+=1;continue
    if aid<=last_id or ts<last_ts:checks['id_time_violations']+=1;continue
    seen.add(aid);last_id=aid;last_ts=ts;quote=price*qty;bucket=ts//900*900
    item=buckets.setdefault(bucket,{'quotes':[],'buyer':0.,'seller':0.})
    item['quotes'].append(quote)
    if side=='true':item['seller']+=quote
    else:item['buyer']+=quote
 out=[]
 for ts,item in sorted(buckets.items()):
  q=np.asarray(item['quotes']);total=float(q.sum());threshold=float(np.quantile(q,.99));top=float(q[q>=threshold].sum())
  out.append({'timestamp':ts,'trade_count':len(q),'quote_volume':total,'buyer_quote_volume':item['buyer'],'seller_quote_volume':item['seller'],'signed_imbalance':(item['buyer']-item['seller'])/total,'max_quote_size':float(q.max()),'mean_quote_size':float(q.mean()),'std_quote_size':float(q.std()),'top_1pct_quote_share':top/total})
 return out,checks

def download(key,target,get=requests.get):
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():return
 if shutil.disk_usage(target.parent).free-RESERVE<=0:raise RuntimeError('storage reserve breached')
 r=get('https://data.binance.vision/'+key,stream=True,timeout=60);r.raise_for_status();size=int(r.headers.get('content-length',0))
 if shutil.disk_usage(target.parent).free-size<RESERVE:raise RuntimeError('download would breach storage reserve')
 part=target.with_suffix(target.suffix+'.part')
 with part.open('wb') as f:
  for chunk in r.iter_content(1024*1024):f.write(chunk)
 part.replace(target)

def write_daily(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 fields=list(rows[0]) if rows else ['timestamp','trade_count','quote_volume','buyer_quote_volume','seller_quote_volume','signed_imbalance','max_quote_size','mean_quote_size','std_quote_size','top_1pct_quote_share']
 with gzip.open(path,'wt',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def build(root):
 c=census_module();objects=c.list_objects(SYMBOL);by,complete,missing,_=c.classify(SYMBOL,objects)
 complete=[d for d in complete if START<=d<=END]
 if missing_in_range:=sorted({d for d in c.expected_dates() if START<=d<=END}-set(complete)):raise ValueError(f'missing dates: {missing_in_range[:3]}')
 manifest_path=root/'manifest.json'
 manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'task':'TASK-0128','symbol':SYMBOL,'start':START,'end':END,'days':{},'gate':{'verdict':'COLLECTING'}}
 for date in complete:
  rec=by[date];raw=root/'raw'/Path(rec['zip']['key']).name;checksum=root/'raw'/Path(rec['checksum']['key']).name;daily=root/'daily'/f'{date}.csv.gz'
  download(rec['checksum']['key'],checksum);download(rec['zip']['key'],raw)
  expected=checksum.read_text().strip().split()[0];digest=hashlib.sha256(raw.read_bytes()).hexdigest()
  if digest!=expected:raise ValueError(f'{date}: checksum mismatch')
  if daily.exists() and date in manifest['days']:continue
  rows,checks=parse_archive(raw);write_daily(daily,rows);manifest['days'][date]={'zip_sha256':digest,'rows':len(rows),'checks':checks}
  manifest_path.parent.mkdir(parents=True,exist_ok=True);manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 return manifest

def main():
 p=argparse.ArgumentParser();p.add_argument('--output-root',default='data/research/btc_aggtrades');a=p.parse_args();print(json.dumps(build(Path(a.output_root)),indent=2,sort_keys=True))
if __name__=='__main__':main()
