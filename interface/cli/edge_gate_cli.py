#!/usr/bin/env python3
"""Edge-gate CLI — E-P5.2 go/no-go.

Runs the standard backtest for one or more strategies, builds the per-strategy
edge ledger (expectancy / PF / win-rate / R:R by regime, net of realistic
fills), and prints the go/no-go verdict. The cheap kill switch before investing
in execution-safety hardening (E-P5.1).

Layering: owns argument parsing + I/O, drives the feature through
``RunBacktestUseCase`` (application), and bridges to the infrastructure edge
ledger/gate via ``bootstrap.edge_gate_runner`` — so this module never imports
infrastructure directly (R1 stays intact).

Exit codes: 0 = GO, 1 = NO_GO, 2 = INSUFFICIENT_DATA, 3 = error.

Examples:
  edge_gate_cli.py --all-strategies --start 365d --end today --symbols BTCUSDT
  edge_gate_cli.py --strategies rsi_strategy momentum --start 2023-01-01 --end 2023-12-31
  edge_gate_cli.py --from-ledger data/results_storage/edge_ledger.json
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

# Ensure project root is importable when invoked as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from domain.enums.strategy_type import StrategyType
from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan
from bootstrap.edge_gate_runner import build_and_evaluate, evaluate_saved_ledger, set_forensic_logging

_EXIT = {"GO": 0, "NO_GO": 1, "DIRECTIONAL_NO_GO": 1, "INSUFFICIENT_DATA": 2}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Edge gate: measure per-strategy edge and decide go/no-go",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    grp = parser.add_mutually_exclusive_group(required=False)
    grp.add_argument("--strategy", type=str, default="rsi_strategy",
                     help="Single strategy to evaluate (default: rsi_strategy)")
    grp.add_argument("--all-strategies", action="store_true",
                     help="Evaluate all available strategies")
    grp.add_argument("--strategies", nargs="+", type=str,
                     help="List of specific strategies (space-separated)")
    grp.add_argument("--from-ledger", type=str,
                     help="Skip backtests; evaluate an existing edge-ledger JSON file")

    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD or relative (e.g. 365d)")
    parser.add_argument("--end", type=str, default="today", help="End date or 'today'")
    parser.add_argument("--symbols", nargs="+", type=str, help="Symbols (default: WFO_COINS env)")
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--fee", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)

    parser.add_argument("--min-trades", type=int, default=30,
                        help="Minimum trades per (strategy,regime) cell (default: 30)")
    parser.add_argument("--min-expectancy", type=float, default=0.0,
                        help="Expectancy must exceed this (default: 0.0)")
    parser.add_argument("--min-profit-factor", type=float, default=1.0,
                        help="Profit factor must exceed this (default: 1.0)")
    parser.add_argument("--ledger", type=str, default="data/results_storage/edge_ledger.json",
                        help="Where to persist the built edge ledger")
    parser.add_argument("--output", type=str, help="Write the full verdict JSON to this file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Keep full per-bar logging (default: quiet for speed)")
    return parser


def _parse_date(date_str: str) -> datetime:
    if date_str == "today":
        return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    if date_str.endswith("d"):
        return datetime.now() - timedelta(days=int(date_str[:-1]))
    return datetime.strptime(date_str, "%Y-%m-%d")


def _print_verdict(report: dict) -> None:
    v = report["verdict"]
    print("\n" + "=" * 60)
    print(f"  EDGE GATE VERDICT: {v['verdict']}")
    print("=" * 60)
    print(f"  {v['summary']}")
    if v["passing"]:
        print(f"\n  Passing cells ({len(v['passing'])}):")
        for c in v["passing"]:
            print(f"    ✅ {c['strategy']} / {c['regime']}: "
                  f"exp={c['expectancy']:.6g} PF={c['profit_factor']} trades={c['trade_count']}")
    if v["failing"]:
        print(f"\n  Failing cells ({len(v['failing'])}):")
        for c in v["failing"]:
            print(f"    ❌ {c['strategy']} / {c['regime']}: {'; '.join(c['reasons'])}")
    attr = report.get("attribution") or {}
    if attr:
        print(f"\n  P&L attribution — total={attr.get('total_pnl', 0):.6g} "
              f"(unattributed={attr.get('unattributed_trades', 0)}, "
              f"unknown_regime={attr.get('unknown_regime_trades', 0)})")
        for regime, pnl in (attr.get("by_regime") or {}).items():
            print(f"    by regime: {regime}: {pnl:.6g}")
    if report.get("ledger_path"):
        print(f"\n  Edge ledger: {report['ledger_path']}")
    print("=" * 60)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Quiet per-bar INFO/DEBUG logging by default — a long-window backtest emits
    # tens of thousands of per-bar log lines, which dominates runtime. The gate
    # only needs the final verdict. Use --verbose to keep full logs.
    if not args.verbose:
        import logging
        logging.disable(logging.INFO)
        # Forensic decision logging is a live audit trail, irrelevant to offline
        # edge measurement; its per-decision validation dominates runtime.
        set_forensic_logging(False)

    try:
        # Mode A: evaluate an existing ledger (no backtests, runnable anywhere).
        if args.from_ledger:
            report = evaluate_saved_ledger(
                args.from_ledger,
                min_trades=args.min_trades,
                min_expectancy=args.min_expectancy,
                min_profit_factor=args.min_profit_factor,
            )
            _print_verdict(report)
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report, f, indent=2, default=str)
            return _EXIT.get(report["verdict"]["verdict"], 3)

        # Mode B: run backtests, then gate.
        if not args.start:
            parser.error("--start is required unless --from-ledger is used")

        start_date, end_date = _parse_date(args.start), _parse_date(args.end)
        if args.symbols:
            symbols = args.symbols
        else:
            from runner_backtest import load_symbols_from_env
            symbols = load_symbols_from_env()

        if args.all_strategies:
            strategies = [s.value for s in StrategyType] + ["crypto_breakout"]
        elif args.strategies:
            strategies = args.strategies
        else:
            strategies = [args.strategy]

        print("🎯 Edge Gate — measuring per-strategy edge before execution spend")
        print(f"   Strategies: {strategies}")
        print(f"   Date Range: {start_date.date()} to {end_date.date()}  Symbols: {symbols}")

        results_by_strategy = {}
        with lifespan() as container:
            use_case = RunBacktestUseCase(
                file_repository=container.resolve("file_repository"),
                backtester_factory=container.resolve("backtester_factory"),
                strategy_provider=container.resolve("backtest_strategy_provider"),
                csv_history_loader=container.resolve("csv_history_loader"),
            )
            for strategy in strategies:
                request = BacktestRequest(
                    symbols=symbols,
                    strategy_names=[strategy],
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=args.capital,
                    fee_rate=args.fee,
                    slippage_factor=args.slippage,
                )
                results_by_strategy[strategy] = use_case.execute(request)

        report = build_and_evaluate(
            results_by_strategy,
            save_path=args.ledger,
            min_trades=args.min_trades,
            min_expectancy=args.min_expectancy,
            min_profit_factor=args.min_profit_factor,
        )
        _print_verdict(report)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
        return _EXIT.get(report["verdict"]["verdict"], 3)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 3
    except Exception as e:
        print(f"\n❌ Edge gate failed: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
