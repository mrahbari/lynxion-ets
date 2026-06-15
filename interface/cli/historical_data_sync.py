#!/usr/bin/env python3
"""Historical data-sync CLI shell (E2.T4c).

Entry point for the scheduled historical-data sync job. Owns process I/O,
builds the composition root, resolves the data ports
(``historical_data_provider_factory`` / ``historical_csv_loader_factory``), and
delegates orchestration to :class:`SyncHistoricalDataUseCase`. Behavior,
arguments, and console output are preserved byte-identically from the legacy
runner.

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.sync_historical_data import SyncHistoricalDataUseCase
from bootstrap.lifecycle import lifespan


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:]) if argv is None else list(argv)

    print("Starting Historical Data Sync Job...")

    with lifespan() as container:
        sync_job = SyncHistoricalDataUseCase(
            settings=container.settings,
            data_provider_factory=container.resolve("historical_data_provider_factory"),
            csv_loader_factory=container.resolve("historical_csv_loader_factory"),
        )

        # If run with 'now' argument, run once and exit
        if len(args) > 0 and args[0] == 'now':
            print("Running one-time sync...")
            sync_job.sync_approved_symbols()
            print("One-time sync completed.")
            return 0

        # Otherwise, start the scheduler
        try:
            sync_job.start_scheduler()
            return 0
        except KeyboardInterrupt:
            print("\nHistorical Data Sync Job stopped by user.")
            return 0
        except Exception as e:
            print(f"Error in Historical Data Sync Job: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
