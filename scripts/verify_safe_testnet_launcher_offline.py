"""No broker, actual process launch, credentials or operational journal access."""
import json
from pathlib import Path
import runpy
import tempfile
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

    def test_normal_launch_mode_never_spawns_after_recovery_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            for proof,code in (({'blocked':True},2),
                               ({'blocked':False,'status_counts':{'PROTECTION_UNKNOWN':1}},0),
                               ({'blocked':False,'status_counts':{'INTENT':1}},0)):
                run=Mock(side_effect=[SimpleNamespace(stdout=''),
                    SimpleNamespace(returncode=code,stdout=json.dumps(proof))])
                child=Mock()
                actual,_=launch(check_only=False,run=run,popen=child,root=directory)
                self.assertEqual(actual,2)
                child.assert_not_called()
                self.assertEqual(list(Path(directory).iterdir()),[])

    def test_normal_launch_uses_testnet_original_journal_and_detached_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'logs').mkdir()
            run=Mock(side_effect=[SimpleNamespace(stdout=''),
                SimpleNamespace(returncode=0,stdout=json.dumps(
                    {'blocked':False,'status_counts':{'FILLED':1}}))])
            child=Mock(return_value=SimpleNamespace(pid=4242))
            code,result=launch(check_only=False,run=run,popen=child,
                               root=root,executable='/synthetic/python')
            self.assertEqual(code,0);self.assertTrue(result['launched'])
            self.assertEqual(result['pid'],4242);child.assert_called_once()
            call=child.call_args
            self.assertEqual(call.args[0],['/synthetic/python','-B','-u',
                'run_trading_system.py','--mode','production','--auto-detect'])
            self.assertEqual(call.kwargs['cwd'],root)
            env=call.kwargs['env']
            self.assertEqual(env['LIVE_TRADING'],'false')
            self.assertEqual(env['BINGX_TESTNET'],'true')
            self.assertEqual(env['BROKER_TESTNET'],'true')
            self.assertEqual(env['LIVE_ORDER_JOURNAL_PATH'],str(root/'data/live_order_journal.json'))
            self.assertTrue(call.kwargs['start_new_session'])
            self.assertTrue(call.kwargs['stdout'].closed)
            self.assertTrue(Path(result['stdout_log']).exists())
            self.assertFalse((root/'data').exists())

    def test_invalid_recovery_json_stops_normal_launch(self):
        child=Mock()
        run=Mock(side_effect=[SimpleNamespace(stdout=''),
            SimpleNamespace(returncode=0,stdout='{broken')])
        code,_=launch(check_only=False,run=run,popen=child)
        self.assertEqual(code,2);child.assert_not_called()

    def test_spawn_failure_is_reported_not_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'logs').mkdir()
            run=Mock(side_effect=[SimpleNamespace(stdout=''),
                SimpleNamespace(returncode=0,stdout=json.dumps(
                    {'blocked':False,'status_counts':{}}))])
            child=Mock(side_effect=OSError('synthetic spawn failure'))
            code,result=launch(check_only=False,run=run,popen=child,root=root)
            self.assertEqual(code,2)
            self.assertNotIn('launched',result);self.assertNotIn('pid',result)
            self.assertFalse((root/'data').exists())

if __name__=='__main__':unittest.main()
