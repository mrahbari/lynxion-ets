import concurrent.futures, datetime, hashlib, json, os, shutil, time
import urllib.request, urllib.error, urllib.parse
from pathlib import Path

ROOT=Path('/Users/mojtaba.rahbari/Sites/python/lynxion-ets/data/research/epic01_mtf_maker/qualification_2026-10-28')
CAP=256*1024*1024
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,url):
        p=urllib.parse.urlparse(url)
        if p.scheme!='https' or not p.hostname or not (p.hostname=='tardis.dev' or p.hostname.endswith('.tardis.dev')):raise RuntimeError('unapproved redirect host')
        return super().redirect_request(req,fp,code,msg,headers,url)

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def get(kind):
    name=f'binance-futures_{kind}_2024-01-01_BTCUSDT.csv.gz'
    url=f'https://datasets.tardis.dev/v1/binance-futures/{kind}/2024/01/01/BTCUSDT.csv.gz'
    partial=ROOT/'raw'/(name+'.partial'); final=ROOT/'raw'/name
    if final.exists() or partial.exists():raise RuntimeError('existing acquisition file; refusing overwrite/retry')
    record={'kind':kind,'symbol':'BTCUSDT','utc_day':'2024-01-01','url':url,'method':'GET',
            'request_utc':now(),'byte_cap':CAP,'filename':name,'source':'TARDIS_VENDOR_NORMALIZED_OBSERVED'}
    digest=hashlib.sha256(); count=0; started=time.monotonic()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),Redirect())
    try:
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'Lynxion-MTF-qualification/1','Accept-Encoding':'identity'}),timeout=15) as r:
            record.update(status=r.status,content_length=r.headers.get('Content-Length'),content_type=r.headers.get('Content-Type'))
            if r.headers.get('Content-Length') and int(r.headers['Content-Length'])>CAP:raise ValueError('declared file exceeds fixed cap')
            with partial.open('xb') as f:
                while True:
                    if time.monotonic()-started>120:raise TimeoutError('fixed download deadline')
                    block=r.read(min(1024*1024,CAP-count+1))
                    if not block:break
                    f.write(block);digest.update(block);count+=len(block)
                    if count>CAP:raise ValueError('compressed-byte cap exceeded')
                f.flush();os.fsync(f.fileno())
            if r.headers.get('Content-Length') and count!=int(r.headers['Content-Length']):raise ValueError('response length mismatch')
        partial.rename(final);record.update(acquisition='COMPLETE_BYTES_ONLY_NOT_QUALIFIED',sha256=digest.hexdigest(),bytes=count)
    except Exception as exc:
        record.update(acquisition='FAILED_NOT_QUALIFIED',error=type(exc).__name__,bytes=count,partial_sha256=digest.hexdigest())
    record['completion_utc']=now();print(json.dumps(record),flush=True);return record

if __name__ == '__main__':
    if shutil.disk_usage(ROOT.parent if ROOT.parent.exists() else ROOT.parents[2]).free<10*1024**3:raise SystemExit('insufficient fixed disk reserve')
    (ROOT/'raw').mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(get,['book_snapshot_5','trades']))
    manifest={'contract_commit':'7eab7ae','scope':'two fixed free samples, no API key/payment/account, no retry',
              'not_a_pilot_extension':True,'raw_files':results,'outcomes_opened':False}
    with (ROOT/'acquisition_manifest.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
    raise SystemExit(0 if all(r['acquisition'].startswith('COMPLETE') for r in results) else 2)
