"""No broker, actual process launch, credentials or operational journal access."""
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

script=Path(__file__).with_name('lynxion_safe_testnet_launcher.py')
launch=runpy.run_path(str(script))['launch']
class LaunchTests(unittest.TestCase):
    def evaluate(self,proof=None,code=0,inventory='',error=None):
        runner=Mock(side_effect=[SimpleNamespace(stdout=inventory),
            error if error else SimpleNamespace(returncode=code,stdout=json.dumps(proof))])
        child=Mock(side_effect=AssertionError('MUST_NOT_SPAWN'))
        result=launch(check_only=True,run=runner,popen=child)
        child.assert_not_called()
        return result,runner
    def test_failed_recovery_cannot_spawn(self):
        self.assertEqual(self.evaluate({'blocked':True},2)[0][0],2)
    def test_success_exit_cannot_hide_unknown(self):
        self.assertEqual(self.evaluate({'blocked':False,'status_counts':{'PROTECTION_UNKNOWN':1}})[0][0],2)
    def test_intent_cannot_spawn(self):
        self.assertEqual(self.evaluate({'blocked':False,'status_counts':{'INTENT':1}})[0][0],2)
    def test_missing_proof_fails_closed(self):
        for proof in ({},{'blocked':False},{'blocked':0,'status_counts':{}},None):
            self.assertEqual(self.evaluate(proof)[0][0],2)
    def test_invalid_counts_fail_closed(self):
        for value in (-1,True,'0',None):
            self.assertEqual(self.evaluate({'blocked':False,'status_counts':{'FILLED':value}})[0][0],2)
    def test_inventory_error_fails_closed(self):
        child=Mock();code,_=launch(run=Mock(side_effect=OSError()),popen=child)
        self.assertEqual(code,2);child.assert_not_called()
    def test_existing_runner_stops_before_recovery(self):
        result,runner=self.evaluate(inventory='123 python run_trading_system.py --mode production')
        self.assertEqual(result[0],2);self.assertEqual(runner.call_count,1)
    def test_clean_check_only_never_spawns(self):
        result,runner=self.evaluate({'blocked':False,'status_counts':{'FILLED':3}})
        self.assertEqual(result,(0,{'blocked':False,'check_only':True,'launched':False}))
        env=runner.call_args.kwargs['env']
        self.assertEqual(env['LIVE_TRADING'],'false');self.assertEqual(env['BINGX_TESTNET'],'true')
    def test_recovery_timeout_stops_launch(self):
        self.assertEqual(self.evaluate(error=TimeoutError())[0][0],2)

if __name__=='__main__':unittest.main()
