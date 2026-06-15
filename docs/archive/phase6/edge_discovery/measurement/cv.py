"""Leakage-proof time-series cross-validation (Phase-6 harness, Step 1).

Purged + embargoed walk-forward and purged k-fold splits. The embargo gap must be
>= the maximum forward-label horizon so a test label cannot overlap any training
observation (López de Prado purging/embargo). Index-based; caller maps to time.
"""
from __future__ import annotations

import numpy as np


def purged_walk_forward(
    n: int, n_splits: int = 5, embargo: int = 0, min_train: int = 30
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Expanding-window walk-forward. Train is everything up to (test_start -
    embargo); the embargo purges observations whose forward label would overlap
    the test window. Train is always strictly BEFORE test (no future leakage).
    """
    if n_splits < 1 or n < (n_splits + 1) * 5:
        return []
    fold = n // (n_splits + 1)
    splits = []
    for k in range(1, n_splits + 1):
        test_start = k * fold
        test_end = (k + 1) * fold if k < n_splits else n
        train_end = max(0, test_start - embargo)
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)
        if len(train_idx) < min_train or len(test_idx) == 0:
            continue
        splits.append((train_idx, test_idx))
    return splits


def purged_kfold(
    n: int, k: int = 5, embargo: int = 0
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Contiguous k test folds; training excludes the test fold plus an embargo
    band on BOTH sides (test folds here are not necessarily future-only, so we
    purge symmetrically). Use walk-forward when strict past-only training matters.
    """
    if k < 2 or n < k * 5:
        return []
    folds = np.array_split(np.arange(n), k)
    splits = []
    for test in folds:
        lo, hi = int(test[0]), int(test[-1])
        mask = np.ones(n, dtype=bool)
        mask[max(0, lo - embargo): min(n, hi + embargo + 1)] = False
        train_idx = np.arange(n)[mask]
        if len(train_idx) < 5:
            continue
        splits.append((train_idx, np.asarray(test)))
    return splits


def assert_no_leakage(
    splits: list[tuple[np.ndarray, np.ndarray]], embargo: int, walk_forward: bool = True
) -> bool:
    """Validate splits: train/test disjoint, embargo gap respected, and (for
    walk-forward) every training index strictly precedes its test window minus
    the embargo. Raises AssertionError on any violation; returns True otherwise.
    """
    for tr, te in splits:
        assert len(np.intersect1d(tr, te)) == 0, "train/test overlap"
        if len(tr) == 0 or len(te) == 0:
            continue
        if walk_forward:
            assert tr.max() < te.min(), "training index not strictly before test"
            assert te.min() - tr.max() - 1 >= embargo, "embargo gap violated"
        else:
            near = np.abs(tr[:, None] - te[None, :]).min() if len(tr) and len(te) else embargo + 1
            assert near > embargo, "embargo band violated in k-fold"
    return True
