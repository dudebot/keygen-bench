#!/usr/bin/env python3
"""Recompute the published official-CE P/H/current-SSM association checks.

This consumes the reviewed public feature table; it does not regenerate features,
download audio, run the listener, fit a model, or select a candidate scalar.
Requires NumPy and SciPy. Original versions: NumPy 2.2.6, SciPy 1.16.1.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

SEED = 20261016
BOOTSTRAP_REPLICATES = 2000
HERE = Path(__file__).resolve().parent


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def correlation(x, y):
    """The frozen analysis's centered Pearson correlation of two rank arrays."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x - x.mean()
    y = y - y.mean()
    denominator = np.linalg.norm(x) * np.linalg.norm(y)
    if denominator <= 1e-14:
        return np.nan
    return float(np.clip(np.dot(x, y) / denominator, -1, 1))


def spearman(x, y):
    return correlation(rankdata(x), rankdata(y))


def model_cluster_interval(x, y, models):
    """Resample whole model directories, including every selected attempt."""
    groups = [np.where(models == group)[0] for group in np.unique(models)]
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(BOOTSTRAP_REPLICATES):
        indices = np.concatenate(
            [groups[j] for j in rng.integers(0, len(groups), size=len(groups))]
        )
        value = spearman(x[indices], y[indices])
        if np.isfinite(value):
            values.append(value)
    return np.percentile(values, [2.5, 97.5]).tolist(), len(values)


def reproduce(rows):
    results = []
    for strict in (False, True):
        cohort = "official_strict" if strict else "official_rowstart"
        eligible = [
            row for row in rows
            if row["complete"].lower() == "true"
            and (not strict or row["strict_timing"].lower() == "true")
        ]
        for prefix in (False, True):
            horizon = "complete_row_prefix_120s" if prefix else "full_song"
            for descriptor in ("P", "H", "current_SSM"):
                feature = ("prefix_" if prefix else "") + descriptor
                pairs = [
                    (number(row[feature]), number(row["official_ce"]), row["model"])
                    for row in eligible
                ]
                pairs = [p for p in pairs if p[0] is not None and p[1] is not None]
                x = np.asarray([p[0] for p in pairs], dtype=float)
                y = np.asarray([p[1] for p in pairs], dtype=float)
                groups = np.asarray([p[2] for p in pairs])
                interval, valid = model_cluster_interval(x, y, groups)
                results.append({
                    "cohort": cohort,
                    "analysis_horizon": horizon,
                    "feature": feature,
                    "n": len(pairs),
                    "models": len(np.unique(groups)),
                    "spearman": spearman(x, y),
                    "pointwise_cluster_ci95_low": interval[0],
                    "pointwise_cluster_ci95_high": interval[1],
                    "valid_bootstrap": valid,
                })
    return results


def check_published(results, path):
    published = json.loads(path.read_text(encoding="utf8"))
    expected = {
        (row["cohort"], row.get("analysis_horizon", row.get("horizon")), row["feature"]): row
        for row in published
    }
    for row in results:
        key = (row["cohort"], row["analysis_horizon"], row["feature"])
        reference = expected[key]
        for field in ("n", "models", "valid_bootstrap"):
            if row[field] != reference[field]:
                raise ValueError(f"Published count mismatch: {key}, {field}")
        for field in ("spearman", "pointwise_cluster_ci95_low", "pointwise_cluster_ci95_high"):
            if not math.isclose(row[field], reference[field], rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"Published numeric mismatch: {key}, {field}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HERE / "data/statistical-input.csv")
    parser.add_argument("--check", action="store_true", help="Fail unless all 12 results match the published association table.")
    parser.add_argument("--out", type=Path, help="Optional JSON output; defaults to stdout.")
    args = parser.parse_args()
    with args.data.open(encoding="utf8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    results = reproduce(rows)
    if args.check:
        check_published(results, HERE / "data/associations.json")
    payload = {
        "scope": "Official CE only; P, H and current SSM; both extraction cohorts and horizons.",
        "source_rows": len(rows),
        "seed": SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "published_checks": "12/12 passed" if args.check else "not requested",
        "interpretation": "Pointwise model-cluster intervals; not human validation or simultaneous discovery intervals.",
        "results": results,
    }
    text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
