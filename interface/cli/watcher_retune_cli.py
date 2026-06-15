"""CLI entry point for watcher-retune gap repair (E5 entry-point rewiring).

The reusable ``WatcherRetuneUseCase`` lives in
``application/data_sync/watcher_retune.py`` and depends only on application ports.
This thin operator-facing CLI is the composition root: it builds the container via
``bootstrap.lifecycle.lifespan`` and resolves the wired ``watcher_retune`` use case
(and its ``data_downloader``), so the application module no longer imports
infrastructure adapters directly.
"""
import argparse
import asyncio
import os
import sys

# Ensure project root is importable when invoked as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bootstrap.lifecycle import lifespan


async def run_with_resources(args, container):
    """Run the watcher retune with container-resolved resources."""
    watcher_retune = container.resolve("watcher_retune")
    # Same cached instance the use case was built with; async-managed for cleanup.
    data_downloader = container.resolve("data_downloader")

    async with data_downloader:
        return watcher_retune.request_repair_sync(
            args.symbol,
            args.start_ts,
            args.end_ts,
            args.timeout
        )


def main():
    """Main entry point for the watcher retune command line tool."""
    parser = argparse.ArgumentParser(description='Run watcher retune operations')
    parser.add_argument('--symbol', type=str, required=True,
                        help='Symbol to repair (e.g. BTC-USDT)')
    parser.add_argument('--from', dest='start_ts', type=int, required=True,
                        help='Start timestamp for the repair interval')
    parser.add_argument('--to', dest='end_ts', type=int, required=True,
                        help='End timestamp for the repair interval')
    parser.add_argument('--timeout', type=int, default=300,
                        help='Maximum time to wait in seconds (default: 300)')

    args = parser.parse_args()

    print(f"Requesting priority repair for {args.symbol} from {args.start_ts} to {args.end_ts}")

    with lifespan() as container:
        success = asyncio.run(run_with_resources(args, container))

    if success:
        print("Repair completed successfully - data is now gap-free!")
        return 0
    else:
        print("Repair timed out - data may still have gaps.")
        return 1


if __name__ == "__main__":
    main()
