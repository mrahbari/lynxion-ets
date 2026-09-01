import importlib.util
from pathlib import Path

def module():
    p=Path(__file__).resolve().parents[2]/'scripts'/'evaluate_independent_basis_c25.py'; s=importlib.util.spec_from_file_location('c25',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_independent_universe_and_identity(monkeypatch,tmp_path):
    m=module(); base=m.mechanics(); captured={}
    def fake_build(*args):
        captured['symbols']=base.SYMBOLS
        return {'candidate':'C-24','protocol':'edge-candidate-register-v23'}
    monkeypatch.setattr(m,'mechanics',lambda:base); monkeypatch.setattr(base,'build_report',fake_build)
    report=m.build_report(tmp_path,tmp_path,tmp_path)
    assert captured['symbols']==m.SYMBOLS
    assert report=={'candidate':'C-25','protocol':'edge-candidate-register-v24'}

def test_mechanics_are_unchanged():
    m=module(); base=m.mechanics()
    assert (base.LOOKBACK,base.FLOOR,base.CONVERGED,base.TIMEOUT,base.PRIMARY_COST)==(2880,.004,.0005,96,.002)
