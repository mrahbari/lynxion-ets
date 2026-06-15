"""CLI entry point for the data-sync loop (E5 entry-point rewiring).

The reusable ``SyncLoop`` lives in ``application/data_sync/sync_loop.py`` and depends
only on the ``SyncManager`` application port. This thin operator-facing CLI is the
composition root: it builds the container via ``bootstrap.lifecycle.lifespan`` and
resolves the wired ``sync_manager`` / ``data_downloader`` adapters, so the
application module no longer imports infrastructure adapters directly.
"""
import argparse
import asyncio
import os
import sys

# Ensure project root is importable when invoked as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bootstrap.lifecycle import lifespan
from application.data_sync.sync_loop import SyncLoop


async def run_with_resources(args, container):
    """Run the sync loop with container-resolved resources."""
    sync_manager = container.resolve("sync_manager")
    # Same cached instance the sync_manager was built with; used as an async
    # context manager for deterministic resource cleanup.
    data_downloader = container.resolve("data_downloader")
    loop = SyncLoop(sync_manager)

    async with data_downloader:
        if args.one_cycle:
            await loop.run_single_cycle(args.symbol)
        else:
            await loop.run_continuous_sync()


def main():
    """Main entry point for the sync loop."""
    parser = argparse.ArgumentParser(description='Run the sync loop')
    parser.add_argument('--one-cycle', action='store_true',
                        help='Run a single sync cycle and exit')
    parser.add_argument('--symbol', type=str,
                        help='Specific symbol to sync (e.g. BTC-USDT)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run in dry-run mode (not implemented in this version)')

    args = parser.parse_args()

    with lifespan() as container:
        asyncio.run(run_with_resources(args, container))


if __name__ == "__main__":
    main()
