"""Opt-in forward exit-evidence runtime bundle for the auto-detection VST runner."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from infrastructure.observability.exit_event_ledger import ExitEventLedger
from infrastructure.observability.position_identity_snapshot import PositionIdentitySnapshot


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("forward exit activation boundary must be UTC")
    return parsed


class ForwardOnlyExitObserver:
    def __init__(self, ledger: ExitEventLedger, boundary_utc: str):
        self.ledger = ledger
        self.boundary_utc = boundary_utc
        self._boundary = _utc(boundary_utc)

    def append(self, event: Dict[str, Any]):
        event_time = _utc(event.get("event_time_utc", ""))
        if event_time <= self._boundary:
            raise ValueError("event is not strictly after the forward activation boundary")
        return self.ledger.append(event)


class ForwardExitRuntimeBundle:
    def __init__(self, root: Path | str, run_id: str, boundary_utc: str, commit: str):
        if not run_id.strip() or not commit.strip():
            raise ValueError("forward exit run id and commit are required")
        self.root = Path(root)
        self.run_id = run_id
        self.boundary_utc = boundary_utc
        _utc(boundary_utc)
        self.identity_store = PositionIdentitySnapshot(self.root / "position_identities.json")
        self.ledger = ExitEventLedger(self.root / "events")
        self.observer = ForwardOnlyExitObserver(self.ledger, boundary_utc)
        self._write_manifest(commit)

    def _write_manifest(self, commit: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / "activation.json"
        payload = {
            "schema_version": 1,
            "run_id": self.run_id,
            "activation_boundary_utc": self.boundary_utc,
            "commit": commit,
            "historical_import_allowed": False,
        }
        rendered = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        if path.exists():
            if path.read_text(encoding="utf-8") != rendered:
                raise ValueError("forward exit activation manifest conflicts with existing cohort")
            return
        temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
        temporary.write_text(rendered, encoding="utf-8")
        os.replace(temporary, path)


def build_forward_exit_runtime_bundle() -> Optional[ForwardExitRuntimeBundle]:
    if os.getenv("LYNXION_FORWARD_EXIT_OBSERVER_ENABLED", "").lower() not in {"1", "true", "yes"}:
        return None
    root = os.getenv(
        "LYNXION_FORWARD_EXIT_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "observability" / "forward_exit"),
    )
    return ForwardExitRuntimeBundle(
        root=root,
        run_id=os.environ["LYNXION_FORWARD_EXIT_RUN_ID"],
        boundary_utc=os.environ["LYNXION_FORWARD_EXIT_BOUNDARY_UTC"],
        commit=os.environ["LYNXION_FORWARD_EXIT_COMMIT"],
    )
