import importlib.util
from pathlib import Path

def module():
    p=Path(__file__).resolve().parents[2]/'scripts'/'evaluate_independent_taker_flow_c22.py'; s=importlib.util.spec_from_file_location('c22',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_universe_is_disjoint_from_c21():
    m=module(); assert set(m.SYMBOLS).isdisjoint(m.c21._base().SYMBOLS)

def test_c22_keeps_five_symbol_breadth_and_35pct_concentration(monkeypatch):
    m=module(); base=m.c21._base(); captured={}
    def fake(*args): captured.update(symbols=base.SYMBOLS,limit=base.MAX_CONCENTRATION); return {'candidate':'x','protocol':'x'}
    monkeypatch.setattr(base,'build_report',fake); monkeypatch.setattr(m.c21,'_base',lambda:base)
    report=m.build_report(Path(),Path(),Path())
    assert captured=={'symbols':m.SYMBOLS,'limit':.35} and report['candidate']=='C-22'
