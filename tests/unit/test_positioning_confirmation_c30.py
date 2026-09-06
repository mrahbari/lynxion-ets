import subprocess
import sys
from pathlib import Path

from scripts import evaluate_positioning_confirmation_c30 as c30

def test_confirmation_uses_disjoint_frozen_identity():
    assert c30.CANDIDATE=='C-30'
    assert c30.PROTOCOL=='edge-candidate-register-v29'
    assert c30.BOOTSTRAP_SEED==300030
    assert set(c30.SYMBOLS)=={'AVAXUSDT','DOGEUSDT','DOTUSDT','LINKUSDT','LTCUSDT'}
    assert not set(c30.SYMBOLS)&set(c30.evaluator.SYMBOLS)
def test_confirmation_has_complete_hash_maps():
    expected=set(c30.SYMBOLS)
    assert all(set(mapping)==expected for mapping in (c30.PRIMARY_PRICE_HASH,c30.REVERSE_PRICE_HASH,c30.METRIC_HASH,c30.FUNDING_HASH))
def test_direct_script_help_resolves_shared_evaluator():
    root=Path(__file__).resolve().parents[2]
    result=subprocess.run([sys.executable,str(root/'scripts/evaluate_positioning_confirmation_c30.py'),'--help'],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
