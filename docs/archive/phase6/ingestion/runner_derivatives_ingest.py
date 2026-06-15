#!/usr/bin/env python3
"""Derivatives Ingestion Runner — thin entry point (Phase-6).

Funding-rate and open-interest ingestion. Argument parsing, composition-root
wiring, and process I/O live in :mod:`interface.cli.derivatives_ingest`; this
shim delegates so the canonical path runs through the container-wired
``IngestDerivativesUseCase``. Imports no infrastructure and constructs no
adapters directly.
"""
import os
import sys

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from interface.cli.derivatives_ingest import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
