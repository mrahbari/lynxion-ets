"""Characterization: run_trading_system structural contract (E2.T5.0, updated E2.T5.3).

IMPORT-SAFETY FINDING (the headline safety result of E2.T5.0):
``run_trading_system`` originally COULD NOT be imported in-process offline. Its
module-top imports pulled heavy/optional deps (``hyperopt`` -> missing
``pkg_resources``; ``dash``/``plotly`` -> not installed) and, on import,
triggered side effects that spawned an uncontrollable tree of child processes.

E2.T5.3 RESOLVED that hazard: the production orchestrator class moved to
``infrastructure.orchestrators.production_trading_orchestrator`` and the runner
became a pure CLI router with NO module-top heavy imports. The orchestrator's
structural contract (lifecycle, the four daemon services, ``stop_system``) is now
pinned against the NEW module; the runner is pinned to be import-hazard-free.

These remain **static** (``ast``) pins so they never import the heavy
infrastructure (the orchestrator module still pulls hyperopt/dash, but only when
production actually runs via the composition root). Behavioral pins for the parts
that ARE safe to import live in the shadow / broker_registry / trading-modes /
production-pilot modules.
"""

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_PATH = _REPO_ROOT / "run_trading_system.py"
_TREE = ast.parse(_SRC_PATH.read_text(encoding="utf-8"))

_ORCH_PATH = _REPO_ROOT / "infrastructure" / "orchestrators" / "production_trading_orchestrator.py"
_ORCH_TREE = ast.parse(_ORCH_PATH.read_text(encoding="utf-8"))


def _module_level_imports(tree):
    modules = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def _find_class(tree, name):
    return next((n for n in tree.body
                 if isinstance(n, ast.ClassDef) and n.name == name), None)


def _find_function(scope, name):
    return next((n for n in ast.walk(scope)
                 if isinstance(n, ast.FunctionDef) and n.name == name), None)


@pytest.mark.unit
def test_cli_exposes_the_six_modes():
    parser_fn = _find_function(_TREE, "create_parser")
    assert parser_fn is not None

    choices = None
    for call in ast.walk(parser_fn):
        if not isinstance(call, ast.Call):
            continue
        if call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == "--mode":
            for kw in call.keywords:
                if kw.arg == "choices" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    choices = {e.value for e in kw.value.elts if isinstance(e, ast.Constant)}
    assert choices == {"optimize", "backtest", "retune", "monitor", "production", "config-test"}


@pytest.mark.unit
def test_orchestrator_lifecycle_contract():
    cls = _find_class(_ORCH_TREE, "ProductionTradingOrchestrator")
    assert cls is not None

    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    assert {
        "initialize_system",
        "_start_background_services",
        "_auto_retune_monitor",
        "_risk_monitoring_loop",
        "_performance_monitoring_loop",
        "run_production_trading",
        "stop_system",
    } <= methods


@pytest.mark.unit
def test_four_background_services_are_registered():
    cls = _find_class(_ORCH_TREE, "ProductionTradingOrchestrator")
    start_fn = _find_function(cls, "_start_background_services")
    assert start_fn is not None

    # Count appends to self.background_threads and collect their string labels.
    append_labels = []
    for call in ast.walk(start_fn):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "append"
                and isinstance(call.func.value, ast.Attribute)
                and call.func.value.attr == "background_threads"):
            arg = call.args[0] if call.args else None
            if isinstance(arg, ast.Tuple) and arg.elts and isinstance(arg.elts[0], ast.Constant):
                append_labels.append(arg.elts[0].value)

    assert len(append_labels) == 5
    assert set(append_labels) == {
        "auto_retune", "risk_monitoring", "performance_monitoring", "broker_reconciliation", "dashboard",
    }



@pytest.mark.unit
def test_stop_system_flips_is_running_false():
    cls = _find_class(_ORCH_TREE, "ProductionTradingOrchestrator")
    stop_fn = _find_function(cls, "stop_system")
    assert stop_fn is not None

    flips_false = False
    for node in ast.walk(stop_fn):
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Attribute) and t.attr == "is_running" for t in node.targets)
                and isinstance(node.value, ast.Constant) and node.value.value is False):
            flips_false = True
    assert flips_false


@pytest.mark.unit
def test_import_hazards_are_removed_from_module_top():
    """E2.T5.3: the runner must no longer eagerly import the heavy infra.

    The previously-pinned hazards (hyperopt via live_execution_engine; dash/plotly
    via live_dashboard) now live behind the composition root, so the runner is
    safe to import in-process. No ``infrastructure.*`` import may remain at module
    top.
    """
    modules = _module_level_imports(_TREE)
    assert "infrastructure.execution.live_execution_engine" not in modules
    assert "infrastructure.adapters.live_dashboard" not in modules
    assert not any(m and m.startswith("infrastructure") for m in modules)


@pytest.mark.unit
def test_single_entrypoint():
    """E2.T5.4: entry-point de-duplication — exactly one main() and one __main__ guard."""
    assert _find_function(_TREE, "main") is not None

    main_guard_count = 0
    for node in _TREE.body:
        if isinstance(node, ast.If):
            test = node.test
            if (isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name) and test.left.id == "__name__"
                    and test.comparators and isinstance(test.comparators[0], ast.Constant)
                    and test.comparators[0].value == "__main__"):
                main_guard_count += 1
    assert main_guard_count == 1
