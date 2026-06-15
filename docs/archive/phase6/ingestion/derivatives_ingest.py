"""Derivatives-ingestion CLI shell (Phase-6).

Owns argument parsing + composition-root wiring for funding-rate / open-interest
ingestion, resolves the derivatives ports from the container, and delegates to
:class:`IngestDerivativesUseCase`. Mirrors the history-download CLI conventions.

Free exchange-API data only; paid feeds are approval-gated and not available here.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.ingest_derivatives import (
    DerivativesIngestRequest, IngestDerivativesUseCase)
from bootstrap.lifecycle import lifespan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Ingest derivatives data (funding rate, open interest)")
    p.add_argument("--classes", default="funding,open_interest",
                   help="comma list: funding,open_interest")
    p.add_argument("--symbols", nargs="+", help="symbols (default: --scope set)")
    p.add_argument("--scope", default="sync", choices=["sync", "approved"])
    p.add_argument("--start", default="365d", help="YYYY-MM-DD or relative (e.g. 30d)")
    p.add_argument("--end", default="today")
    p.add_argument("--oi-timeframe", default="1h")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--output", help="optional JSON results file")
    return p


def _to_ms(s: str) -> int:
    s = s.strip().lower()
    now_ms = int(time.time() * 1000)
    if s in ("today", "now"):
        return now_ms
    if s.endswith("d") and s[:-1].isdigit():
        return now_ms - int(s[:-1]) * 86_400_000
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _resolve_symbols(args) -> List[str]:
    if args.symbols:
        return [s.upper() for s in args.symbols]
    from application.symbol_management.centralized_symbol_manager import (
        get_approved_symbols, get_unified_symbols)
    return sorted(get_approved_symbols()) if args.scope == "approved" else list(get_unified_symbols())


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    symbols = _resolve_symbols(args)
    req = DerivativesIngestRequest(
        symbols=symbols, start_ms=_to_ms(args.start), end_ms=_to_ms(args.end),
        classes=[c.strip() for c in args.classes.split(",") if c.strip()],
        oi_timeframe=args.oi_timeframe, exchange=args.exchange)
    print(f"🚀 Derivatives ingestion | {len(symbols)} symbols | classes={req.classes} "
          f"| {args.start}->{args.end}")
    try:
        with lifespan() as container:
            use_case = IngestDerivativesUseCase(
                downloader=container.resolve("derivatives_downloader"),
                store=container.resolve("derivatives_store"))
            summary = use_case.execute(req)
        print(json.dumps(summary, indent=2, default=str))
        if args.output:
            with open(args.output, "w") as f:
                json.dump(summary, f, indent=2, default=str)
        errs = sum(v.get("errors", 0) for v in summary.values() if isinstance(v, dict))
        return 1 if errs else 0
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Derivatives ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
