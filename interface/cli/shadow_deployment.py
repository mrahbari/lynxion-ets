#!/usr/bin/env python3
"""Shadow-deployment CLI shell (E2.T5.1).

Owns argument parsing and process I/O for the shadow (paper) trading loop,
builds the composition root, resolves the shadow ports
(``shadow_strategy_provider`` / ``shadow_csv_loader_factory`` /
``shadow_kpi_reporter``), and delegates orchestration to
:class:`ShadowDeploymentUseCase`. CLI arguments, console output, the cyclic
loop, report file naming, and KeyboardInterrupt handling are preserved verbatim
from the legacy ``runner_shadow_deployment``.

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.run_shadow_deployment import ShadowDeploymentUseCase
from bootstrap.lifecycle import lifespan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run shadow deployment of trading strategies')
    parser.add_argument('--symbols', nargs='+', required=True, help='Symbols to trade')
    parser.add_argument('--strategies', nargs='+', required=True, help='Strategies to use')
    parser.add_argument('--capital', type=float, default=100000.0, help='Initial capital')
    parser.add_argument('--risk-per-trade', type=float, default=0.02, help='Risk per trade')
    parser.add_argument('--interval', type=int, default=60, help='Interval between cycles in seconds')
    parser.add_argument('--report', action='store_true', help='Generate and save report')
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for shadow deployment"""
    parser = build_parser()
    args = parser.parse_args(argv)

    with lifespan() as container:
        # Initialize shadow deployment system
        shadow_system = ShadowDeploymentUseCase(
            settings=container.settings,
            symbols=args.symbols,
            strategies=args.strategies,
            initial_capital=args.capital,
            risk_per_trade=args.risk_per_trade,
            strategy_provider=container.resolve("shadow_strategy_provider"),
            csv_loader_factory=container.resolve("shadow_csv_loader_factory"),
            kpi_reporter=container.resolve("shadow_kpi_reporter"),
        )

        print(f"🚀 Starting shadow deployment for {args.symbols} with strategies {args.strategies}")
        print(f"   Initial Capital: ${args.capital:,.2f}")
        print(f"   Risk Per Trade: {args.risk_per_trade:.2%}")
        print(f"   Cycle Interval: {args.interval}s")

        report_dir = os.path.join(".", "data", "shadow_report")
        os.makedirs(report_dir, exist_ok=True)

        try:
            cycle_count = 0
            while True:
                shadow_system.run_shadow_cycle()
                cycle_count += 1

                # Generate report periodically
                if args.report and cycle_count % 10 == 0:  # Every 10 cycles
                    report = shadow_system.get_shadow_report()
                    report_filename = os.path.join(report_dir, f"shadow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                    with open(report_filename, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                    print(f"   Saved shadow report to {report_filename}")

                time.sleep(args.interval)  # Run every interval seconds
        except KeyboardInterrupt:
            print("\n🛑 Shadow deployment stopped by user")

            # Generate final report
            if args.report:
                report = shadow_system.get_shadow_report()
                final_report_filename = os.path.join(report_dir, f"final_shadow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(final_report_filename, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"   Saved final shadow report to {final_report_filename}")
        except Exception as e:
            print(f"\n❌ Shadow deployment error: {e}")
            import traceback
            traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
