#!/usr/bin/env python3
"""Resume the pinned C-33 collector only after exact source-blob verification."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from requests import RequestException
from websockets.exceptions import ConnectionClosed

try:
    from scripts.collect_c33_liquidation_events import InvalidC33Event, activate, collect
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from collect_c33_liquidation_events import InvalidC33Event, activate, collect


COLLECTOR_PATH = "scripts/collect_c33_liquidation_events.py"
MAX_RECONNECT_DELAY_SECONDS = 60


def resolve_pinned_commit(
    manifest_path: Path,
    git_output: Callable[[list[str]], str] | None = None,
) -> str:
    if git_output is None:
        def git_output(arguments: list[str]) -> str:
            return subprocess.run(
                ["git", *arguments], check=True, capture_output=True, text=True
            ).stdout.strip()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidC33Event("activation manifest is unreadable") from error
    pinned = manifest.get("collector_commit")
    if not isinstance(pinned, str) or not pinned:
        raise InvalidC33Event("activation manifest collector commit is invalid")
    current_blob = git_output(["rev-parse", f"HEAD:{COLLECTOR_PATH}"])
    pinned_blob = git_output(["rev-parse", f"{pinned}:{COLLECTOR_PATH}"])
    if not current_blob or current_blob != pinned_blob:
        raise InvalidC33Event("collector source differs from the activation commit")
    return pinned


async def supervise(
    output: Path,
    activation_boundary: int,
    *,
    collect_fn: Callable[[Path, int], object] = collect,
    sleep_fn: Callable[[float], object] = asyncio.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
    max_attempts: int | None = None,
) -> None:
    """Restart clean sessions after transient public-network failures."""
    delay = 1
    attempts = 0
    while max_attempts is None or attempts < max_attempts:
        attempts += 1
        started = monotonic_fn()
        try:
            await collect_fn(output, activation_boundary)  # type: ignore[misc]
        except (OSError, asyncio.TimeoutError, RequestException, ConnectionClosed) as error:
            print(json.dumps({
                "event": "c33_transient_disconnect",
                "attempt": attempts,
                "error_type": type(error).__name__,
                "error": str(error),
            }, sort_keys=True), file=sys.stderr, flush=True)
        if monotonic_fn() - started >= 300:
            delay = 1
        await sleep_fn(delay)  # type: ignore[misc]
        delay = min(delay * 2, MAX_RECONNECT_DELAY_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/research/c33/events.jsonl"))
    parser.add_argument(
        "--activation-manifest", type=Path, default=Path("data/research/c33/activation_manifest.json")
    )
    parser.add_argument("--enable-network", action="store_true")
    args = parser.parse_args()
    if not args.enable_network:
        raise SystemExit("network collection is fail-closed; pass --enable-network explicitly")
    pinned = resolve_pinned_commit(args.activation_manifest)
    manifest = activate(args.activation_manifest, args.output, commit=pinned)
    asyncio.run(supervise(args.output, int(manifest["activation_boundary"])))


if __name__ == "__main__":
    main()
