#!/usr/bin/env python3
"""Fetch and validate the frozen TASK-0114 Binance taker-flow panel."""

from __future__ import annotations

import argparse, csv, gzip, hashlib, importlib.util, io, json, math, re, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
import requests

SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
START, END = date(2023, 1, 1), date(2026, 8, 29)
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DATA = "https://data.binance.vision/"
COLUMNS = ("open_time", "open", "high", "low", "close", "volume", "close_time",
           "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore")
PATTERN = re.compile(r"-(\d{4}-\d{2}-\d{2})\.zip$")

def _premium():
    p=Path(__file__).with_name("fetch_binance_premium_index_panel.py")
    s=importlib.util.spec_from_file_location("premium_common",p); m=importlib.util.module_from_spec(s)
    assert s.loader; s.loader.exec_module(m); return m

def list_archives(symbol, start=START, end=END, get=requests.get):
    prefix=f"data/futures/um/daily/klines/{symbol}/15m/"; keys=[]; token=None
    while True:
        params={"list-type":"2","prefix":prefix,"max-keys":1000}
        if token: params["continuation-token"]=token
        r=get(S3,params=params,timeout=30); r.raise_for_status(); root=ElementTree.fromstring(r.content)
        ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
        for item in root.findall("s:Contents",ns):
            key=item.findtext("s:Key",namespaces=ns) or ""; match=PATTERN.search(key)
            if match and start <= date.fromisoformat(match.group(1)) <= end: keys.append(key)
        if root.findtext("s:IsTruncated",default="false",namespaces=ns)!="true": break
        token=root.findtext("s:NextContinuationToken",namespaces=ns)
        if not token: raise ValueError(f"{symbol}: missing continuation token")
    return sorted(set(keys))

def download_archive(key, raw_root, get=requests.get):
    common=_premium()._common(); filename=Path(key).name; symbol=key.split("/klines/",1)[1].split("/",1)[0]
    target=raw_root/symbol/filename; c=get(DATA+key+".CHECKSUM",timeout=30); c.raise_for_status()
    expected=common.expected_checksum(c.text,filename)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==expected:
        return {"key":key,"sha256":expected,"bytes":target.stat().st_size,"cached":True}
    r=get(DATA+key,timeout=60); r.raise_for_status(); payload=r.content
    if hashlib.sha256(payload).hexdigest()!=expected: raise ValueError(f"{key}: checksum mismatch")
    target.parent.mkdir(parents=True,exist_ok=True); part=target.with_suffix(".zip.part")
    part.write_bytes(payload); part.replace(target)
    return {"key":key,"sha256":expected,"bytes":len(payload),"cached":False}

def parse_archive(path):
    common=_premium(); checks={"raw_rows":0,"schema_violations":0,"numeric_violations":0,
        "timestamp_violations":0,"ohlc_violations":0,"flow_violations":0}; rows=[]
    with zipfile.ZipFile(path) as z:
        members=[n for n in z.namelist() if n.endswith('.csv')]
        if len(members)!=1: raise ValueError(f"{path.name}: expected one CSV")
        for raw in csv.reader(io.TextIOWrapper(z.open(members[0]),encoding='utf-8')):
            if raw and raw[0]=='open_time':
                if tuple(raw)!=COLUMNS: checks["schema_violations"]+=1
                continue
            checks["raw_rows"]+=1
            if len(raw)!=12: checks["schema_violations"]+=1; continue
            try:
                opened,closed=common.epoch_seconds(raw[0]),common.epoch_seconds(raw[6])
                o,h,l,c=map(float,raw[1:5]); quote=float(raw[7]); count=int(raw[8]); taker=float(raw[10])
                if not all(math.isfinite(v) for v in (o,h,l,c,quote,taker)): raise ValueError
            except (ValueError,TypeError,OverflowError): checks["numeric_violations"]+=1; continue
            if opened%900 or closed!=opened+899: checks["timestamp_violations"]+=1; continue
            if min(o,h,l,c)<=0 or h<max(o,c,l) or l>min(o,c,h): checks["ohlc_violations"]+=1; continue
            if quote<0 or taker<0 or taker>quote or count<0: checks["flow_violations"]+=1; continue
            rows.append((opened,o,h,l,c,quote,count,taker))
    return rows,checks

def normalize(symbol,records,raw_root,out_root):
    totals={"archives":len(records),"raw_rows":0,"unique_rows":0,"exact_duplicates":0,
        "conflicting_duplicates":0,"schema_violations":0,"numeric_violations":0,
        "timestamp_violations":0,"ohlc_violations":0,"flow_violations":0,"missing_intervals":0}
    by={}
    for rec in sorted(records,key=lambda x:x["key"]):
        rows,checks=parse_archive(raw_root/symbol/Path(rec["key"]).name)
        for k,v in checks.items(): totals[k]+=v
        for row in rows:
            old=by.get(row[0])
            if old is None: by[row[0]]=row
            elif old==row: totals["exact_duplicates"]+=1
            else: totals["conflicting_duplicates"]+=1
    rows=[by[k] for k in sorted(by)]; totals["unique_rows"]=len(rows)
    totals["missing_intervals"]=sum(max(0,(b[0]-a[0])//900-1) for a,b in zip(rows,rows[1:]))
    target=out_root/f"{symbol}.csv.gz"; target.parent.mkdir(parents=True,exist_ok=True); part=target.with_suffix('.gz.part')
    digest=hashlib.sha256()
    with gzip.open(part,'wt',newline='',encoding='utf-8') as h:
        w=csv.writer(h); w.writerow(("timestamp","open","high","low","close","quote_volume","count","taker_buy_quote_volume"))
        for row in rows: w.writerow(row); digest.update((",".join(map(str,row))+"\n").encode())
    part.replace(target); totals.update({"first_timestamp":rows[0][0],"last_timestamp":rows[-1][0],
        "sha256":digest.hexdigest(),"file":str(target)}); return totals

def build(root,workers=32,symbols=SYMBOLS,task="TASK-0114"):
    raw,out=root/'raw',root/'normalized'; listings={s:list_archives(s) for s in symbols}; records={s:[] for s in symbols}
    jobs=[(s,k) for s,ks in listings.items() for k in ks]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(download_archive,k,raw):s for s,k in jobs}
        for n,f in enumerate(as_completed(futures),1):
            records[futures[f]].append(f.result())
            if n%500==0 or n==len(jobs): print(f"downloaded/verified {n}/{len(jobs)}",flush=True)
    summaries={s:normalize(s,records[s],raw,out) for s in symbols}
    core=sum(v[k] for v in summaries.values() for k in ("conflicting_duplicates","schema_violations","numeric_violations","timestamp_violations","ohlc_violations","flow_violations"))
    adequate=all(v["unique_rows"]>=120_000 for v in summaries.values())
    manifest={"task":task,"source":DATA,"symbols":summaries,"archives":records,
      "gate":{"core_integrity_violations":core,"source_gap_intervals":sum(v["missing_intervals"] for v in summaries.values()),"adequate_coverage":adequate,"verdict":"KEEP" if core==0 and adequate else "REJECT"}}
    root.mkdir(parents=True,exist_ok=True); (root/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n"); return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output-root',default='data/research/taker_flow'); p.add_argument('--workers',type=int,default=32); p.add_argument('--symbols',nargs='+',default=list(SYMBOLS)); p.add_argument('--task',default='TASK-0114'); a=p.parse_args()
    report=build(Path(a.output_root),a.workers,tuple(a.symbols),a.task); print(json.dumps({"symbols":report["symbols"],"gate":report["gate"]},indent=2,sort_keys=True))
