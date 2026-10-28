#!/usr/bin/env python3
"""Read-only documentation manifest verifier. No application import/network."""
import hashlib, json
from pathlib import Path
root = Path(__file__).resolve().parent
manifest = json.loads((root / 'Package-SHA256.json').read_text())
bad = []
for name, expected in manifest.items():
    target = root / name
    if not target.is_file() or target.is_symlink():
        bad.append(name)
    elif hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        bad.append(name)
if bad:
    print('FAIL: mismatched or missing entries:', bad)
    raise SystemExit(1)
print('PASS:', len(manifest), 'documentation file checksums; not trading/runtime validation')
