"""CSV + provenance store for derivatives ingestion.

Implements domain.ports.derivatives_data.DerivativesStore using the repo's
existing storage conventions: epoch-seconds integer ``timestamp`` first column,
atomic writes, sorted + de-duplicated rows, idempotent merge with any existing
file, and a sidecar provenance JSON shaped like data/provenance/*_provenance.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import List

from domain.ports.derivatives_data import DerivativesStore


def storage_symbol(symbol: str) -> str:
    """BTCUSDT / ETH/USDT:USDT -> BTC-USDT (repo storage convention)."""
    s = symbol.replace("/", "").replace(":USDT", "").upper()
    if s.endswith("USDT") and "-" not in s:
        return f"{s[:-4]}-USDT"
    return s


def _validate(rows: List[dict], columns: List[str]) -> List[dict]:
    seen, out = set(), []
    for r in rows:
        ts = r.get("timestamp")
        if ts is None:
            continue
        ts = int(ts)
        if ts <= 0 or ts > 4102444800:
            raise ValueError(f"timestamp {ts} is not epoch-seconds (ms not converted?)")
        if ts in seen:
            continue
        vals, ok = {}, True
        for c in columns[1:]:
            try:
                vals[c] = float(r.get(c))
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            seen.add(ts)
            out.append({"timestamp": ts, **vals})
    out.sort(key=lambda x: x["timestamp"])
    return out


def _read(path: str, columns: List[str]) -> List[dict]:
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                out.append({"timestamp": int(r["timestamp"]),
                            **{c: float(r[c]) for c in columns[1:] if r.get(c) not in (None, "")}})
            except (ValueError, KeyError):
                continue
    return out


class CsvDerivativesStore(DerivativesStore):
    def __init__(self, raw_root: str = os.path.join("data", "history", "raw"),
                 prov_root: str = os.path.join("data", "provenance")):
        self.raw_root = raw_root
        self.prov_root = prov_root

    def write_series(self, data_class: str, symbol: str, rows: List[dict],
                     columns: List[str], source: str, exchange: str) -> dict:
        rows = _validate(rows, columns)
        path = os.path.join(self.raw_root, data_class, f"{storage_symbol(symbol)}.csv")
        if os.path.exists(path):
            by_ts = {r["timestamp"]: r for r in _read(path, columns)}
            for r in rows:
                by_ts[r["timestamp"]] = r
            rows = sorted(by_ts.values(), key=lambda x: x["timestamp"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=columns)
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c) for c in columns})
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        prov_path = self._write_provenance(data_class, symbol, path, rows, columns, source, exchange)
        return {"symbol": symbol, "data_class": data_class, "rows_total": len(rows),
                "path": path, "provenance": prov_path}

    def _write_provenance(self, data_class, symbol, path, rows, columns, source, exchange) -> str:
        with open(path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        prov = {"source": source, "exchange": exchange,
                "symbol": symbol.replace("-", ""), "data_class": data_class,
                "checksum": checksum,
                "download_timestamp": datetime.now(timezone.utc).isoformat(),
                "row_count": len(rows),
                "date_range": {"start": str(rows[0]["timestamp"]) if rows else None,
                               "end": str(rows[-1]["timestamp"]) if rows else None},
                "columns": columns, "file_path": path}
        os.makedirs(self.prov_root, exist_ok=True)
        prov_path = os.path.join(self.prov_root, f"{storage_symbol(symbol)}_{data_class}_provenance.json")
        with open(prov_path, "w") as f:
            json.dump(prov, f, indent=2)
        return prov_path
