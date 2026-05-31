#!/usr/bin/env python3
"""Compare L2 scores from baseline vs tuned hybrid run on supplement CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = PROJECT_ROOT / "artifacts" / "run_20260529_193015"
DEFAULT_TUNED = PROJECT_ROOT / "artifacts" / "run_20260531_l2_hybrid"
SUPPLEMENT_DIR = PROJECT_ROOT / "dataset" / "l2_supplement"

SKIP = {"timestamp", "label", "hour", "minute", "second", "scenario", "collector_type", "source_file", "os", "level", "split_group", "session_id", "capture_group"}


class L2Ensemble:
    def __init__(self, run_dir: Path):
        manifest = json.loads((run_dir / "ensemble_manifest.json").read_text())
        cfg = manifest["per_level"]["2"]
        self.features: List[str] = list(cfg["features"])
        self.models = []
        for entry in cfg["models"]:
            path = Path(entry["path"])
            if not path.is_file():
                alt = run_dir / "level_2" / path.parent.name / path.name
                path = alt if alt.is_file() else run_dir / path.name
            self.models.append(joblib.load(path))

    def score(self, row: Dict[str, Any]) -> float:
        vector = []
        for name in self.features:
            val = row.get(name, 0)
            try:
                vector.append(float(val))
            except (TypeError, ValueError):
                vector.append(0.0)
        X = np.array([vector])
        probs = []
        for model in self.models:
            if hasattr(model, "predict_proba"):
                probs.append(float(model.predict_proba(X)[0, 1]))
            else:
                probs.append(float(model.predict(X)[0]))
        return float(np.mean(probs)) if probs else 0.0


def load_rows(path: Path, limit: int | None = None) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def summarize(scores: List[float]) -> str:
    if not scores:
        return "n=0"
    return (
        f"n={len(scores)} median={statistics.median(scores):.4f} "
        f"mean={statistics.mean(scores):.4f} max={max(scores):.4f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline L2 score comparison")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--tuned", type=Path, default=DEFAULT_TUNED)
    parser.add_argument("--supplement-dir", type=Path, default=SUPPLEMENT_DIR)
    args = parser.parse_args()

    baseline = L2Ensemble(args.baseline)
    tuned = L2Ensemble(args.tuned)

    print(f"Baseline: {args.baseline.name}")
    print(f"Tuned:    {args.tuned.name}")
    print()

    csv_files = sorted(args.supplement_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files in {args.supplement_dir}", file=sys.stderr)
        return 1

    print(f"{'file':<32} {'baseline':<40} {'tuned':<40}")
    print("-" * 112)

    for path in csv_files:
        rows = load_rows(path)
        b_scores = [baseline.score(r) for r in rows]
        t_scores = [tuned.score(r) for r in rows]
        print(f"{path.name:<32} {summarize(b_scores):<40} {summarize(t_scores):<40}")

    benign_path = args.supplement_dir / "demo_vm_benign.csv"
    if benign_path.is_file():
        rows = load_rows(benign_path)
        mid = rows[len(rows) // 2]
        b = baseline.score(mid)
        t = tuned.score(mid)
        print()
        print(f"Median benign row L2: baseline={b:.4f} tuned={t:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
