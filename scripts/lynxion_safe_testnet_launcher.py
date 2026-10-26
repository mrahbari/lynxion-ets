"""Operator-invoked TESTNET launcher. No launch after failed recovery.

This is not a reconciliation tool: it never clears UNKNOWN or edits a journal.
The trading CLI's own recovery gate remains the final check against state changes.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/Users/mojtaba.rahbari/Sites/python/lynxion-ets')
RECOVERY = '''import json,runpy,sys
try:
 d=runpy.run_path(sys.argv[1]); r=d['LiveOrderJournal'](sys.argv[2]).recover()
 c=r['status_counts']; blocked=any(c.get(s,0) for s in ('INTENT','PROTECTION_UNKNOWN'))
 print(json.dumps({'blocked':bool(blocked),'status_counts':c}))
 sys.exit(2 if blocked else 0)
except Exception:
 print(json.dumps({'blocked':True,'recovery_error':True}));sys.exit(2)
'''

def launch(*, check_only=False, run=subprocess.run, popen=subprocess.Popen,
           root=ROOT, executable=sys.executable):
    root=Path(root)
    env=dict(os.environ)
    env.update(BINGX_TESTNET='true', BROKER_TESTNET='true', LIVE_TRADING='false',
               DEFAULT_BROKER='bingx',LIVE_ORDER_JOURNAL_PATH=str(root/'data/live_order_journal.json'))
    try:
        inventory=run(['/bin/ps','-axo','pid=,command='],capture_output=True,text=True,check=True)
        if any('run_trading_system.py' in line and 'python' in line.lower()
               and ' -c ' not in line for line in inventory.stdout.splitlines()):
            return 2, {'blocked':True,'reason':'EXISTING_RUNNER'}
        recovery=run([executable,'-I','-B','-c',RECOVERY,
                      str(root/'infrastructure/execution/live_order_journal.py'),
                      env['LIVE_ORDER_JOURNAL_PATH']],capture_output=True,text=True,
                     env=env,timeout=20)
        if recovery.returncode != 0:
            return 2, {'blocked':True,'reason':'JOURNAL_RECOVERY_BLOCKED'}
        proof=json.loads(recovery.stdout)
        counts=proof.get('status_counts')
        if (proof.get('blocked') is not False or not isinstance(counts,dict)
                or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in counts.values())
                or any(counts.get(s,0) for s in ('INTENT','PROTECTION_UNKNOWN'))):
            return 2, {'blocked':True,'reason':'INVALID_RECOVERY_PROOF'}
        if check_only:
            return 0, {'blocked':False,'check_only':True,'launched':False}
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        log=root/'logs'/('runner-testnet-'+stamp+'.log')
        with log.open('x') as output:
            p=popen([executable,'-B','-u','run_trading_system.py','--mode','production','--auto-detect'],
                    cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=output,
                    stderr=subprocess.STDOUT,start_new_session=True)
        return 0, {'launched':True,'pid':p.pid,'stdout_log':str(log),
                   'note':'Spawn only; not proof of readiness. Inspect CLI recovery and runtime output.'}
    except Exception:
        return 2, {'blocked':True,'reason':'PREFLIGHT_OR_LAUNCH_ERROR'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check-only',action='store_true')
    code,result=launch(check_only=ap.parse_args().check_only)
    print(json.dumps(result));raise SystemExit(code)
