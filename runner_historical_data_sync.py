#!/usr/bin/env python3
"""Historical Data Sync Runner - thin entry point (E2.T4c).

Orchestration now lives in :class:`application.use_cases.sync_historical_data.SyncHistoricalDataUseCase`
and process I/O lives in :mod:`interface.cli.historical_data_sync`. This shim
delegates so existing invocations keep working unchanged. The runner no longer
imports infrastructure nor constructs adapters/services; all wiring happens in
the composition root.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Backward-compatible entry point; delegates to the CLI shell."""
    from interface.cli.historical_data_sync import main as cli_main
    sys.exit(cli_main())


if __name__ == "__main__":
    main()
