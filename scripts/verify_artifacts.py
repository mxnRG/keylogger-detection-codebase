#!/usr/bin/env python3
"""Verify ML training run artifacts for completeness and common issues."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import joblib


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify artifacts from train_ml.py")
    parser.add_argument(
        "--run-dir",
        type=str,
        default="",
        help="Path to artifacts/run_<timestamp> (default: latest under artifacts/)",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=str(Path(__file__).resolve().parent.parent / "artifacts"),
        help="Artifacts root directory",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit non-zero if any warnings are raised",
    )
    return parser.parse_args()


def find_latest_run(artifacts_dir: Path) -> Path:
    runs = sorted(artifacts_dir.glob("run_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        raise FileNotFoundError(f"No run_* directories in {artifacts_dir}")
    return runs[0]


def add_issue(
    issues: Dict[str, List[str]],
    severity: str,
    message: str,
) -> None:
    issues.setdefault(severity, []).append(message)


def verify_run(run_dir: Path) -> Dict[str, Any]:
    issues: Dict[str, List[str]] = {}
    report: Dict[str, Any] = {"run_dir": str(run_dir), "checks": {}}

    required_json = [
        "metrics.json",
        "dataset_quality.json",
        "feature_dive.json",
        "ensemble_manifest.json",
        "evaluation.json",
    ]
    for name in required_json:
        path = run_dir / name
        if not path.exists():
            add_issue(issues, "errors", f"Missing required file: {name}")
        else:
            report["checks"][name] = "present"

    metrics_path = run_dir / "metrics.json"
    if not metrics_path.exists():
        report["issues"] = issues
        return report

    with open(metrics_path) as f:
        metrics = json.load(f)

    report["run_id"] = metrics.get("run_id")
    levels = metrics.get("levels", {})
    report["checks"]["levels_trained"] = list(levels.keys())

    evaluation_path = run_dir / "evaluation.json"
    evaluation: Dict[str, Any] = {}
    has_evaluation = evaluation_path.exists()
    if has_evaluation:
        with open(evaluation_path) as f:
            evaluation = json.load(f)
        has_tier_b = "B" in evaluation.get("tiers", {})
    else:
        has_tier_b = False

    if not levels and not has_tier_b:
        add_issue(issues, "errors", "metrics.json has no trained levels and no tier B eval")

    expected_levels = {"2", "3", "4"}
    missing_levels = expected_levels - set(levels.keys())
    if missing_levels and not has_tier_b:
        add_issue(
            issues,
            "warnings",
            f"Expected levels {sorted(expected_levels)} but missing: {sorted(missing_levels)}",
        )

    manifest_path = run_dir / "ensemble_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

        per_level = manifest.get("per_level", {})
        if not per_level and manifest.get("models"):
            add_issue(
                issues,
                "warnings",
                "ensemble_manifest uses legacy flat model list (not per_level)",
            )

        for level_key, level_info in per_level.items():
            models = level_info.get("models", [])
            features = level_info.get("features", [])
            if not features:
                add_issue(
                    issues,
                    "errors",
                    f"Level {level_key}: no feature list in ensemble manifest",
                )
            for entry in models:
                model_path = Path(entry.get("path", ""))
                if not model_path.is_file():
                    add_issue(
                        issues,
                        "errors",
                        f"Level {level_key}: missing joblib at {model_path}",
                    )
                else:
                    try:
                        model = joblib.load(model_path)
                        n_features = getattr(model, "n_features_in_", None)
                        if n_features is not None and len(features) != n_features:
                            add_issue(
                                issues,
                                "errors",
                                f"Level {level_key} {entry.get('model')}: "
                                f"manifest features ({len(features)}) != "
                                f"model.n_features_in_ ({n_features})",
                            )
                    except Exception as exc:
                        add_issue(
                            issues,
                            "errors",
                            f"Failed to load {model_path}: {exc}",
                        )

                png_dir = model_path.parent
                model_name = entry.get("model", "model")
                for suffix in ("_roc_curve.png", "_pr_curve.png", "_confusion_matrix.png"):
                    png = png_dir / f"{model_name}{suffix}"
                    if not png.exists():
                        add_issue(issues, "warnings", f"Missing plot: {png}")

    for level_key, level_report in levels.items():
        split = level_report.get("split", {})
        method = split.get("split_method", "unknown")
        if method == "stratified_fallback":
            add_issue(
                issues,
                "warnings",
                f"Level {level_key}: used stratified_fallback split (val may equal test)",
            )
        if split.get("test_equals_val"):
            add_issue(
                issues,
                "errors",
                f"Level {level_key}: test set equals validation set",
            )

        for model_name, model_metrics in level_report.get("models", {}).items():
            for key in ("val_auc", "test_auc", "val_ap", "test_ap"):
                val = model_metrics.get(key)
                if val is None:
                    add_issue(
                        issues,
                        "errors",
                        f"Level {level_key} {model_name}: missing {key}",
                    )
                elif val >= 0.999:
                    add_issue(
                        issues,
                        "warnings",
                        f"Level {level_key} {model_name}: suspiciously perfect {key}={val}",
                    )
                elif val < 0.5:
                    add_issue(
                        issues,
                        "warnings",
                        f"Level {level_key} {model_name}: weak {key}={val} (below random)",
                    )

        drops = level_report.get("feature_drops", {})
        separators = [
            feat
            for feat, reasons in drops.items()
            if "single_threshold_separator" in reasons
        ]
        if separators:
            add_issue(
                issues,
                "warnings",
                f"Level {level_key}: separator features dropped: {separators[:8]}",
            )

    feature_dive_path = run_dir / "feature_dive.json"
    if feature_dive_path.exists():
        with open(feature_dive_path) as f:
            feature_dive = json.load(f)
        overall = feature_dive.get("overall", {})
        leakage = overall.get("leakage_flags", [])
        if leakage:
            add_issue(
                issues,
                "warnings",
                f"feature_dive overall leakage_flags: {len(leakage)} features",
            )
        report["checks"]["leakage_flag_count"] = len(leakage)

    ingestion = metrics.get("ingestion", {})
    report["checks"]["ingestion_files"] = ingestion.get("files_loaded", [])
    if ingestion.get("files_skipped"):
        add_issue(
            issues,
            "warnings",
            f"Ingestion skipped files: {ingestion['files_skipped']}",
        )

    if has_evaluation:
        report["checks"]["evaluation"] = "present"
        tiers = evaluation.get("tiers", {})
        if "B" not in tiers:
            add_issue(issues, "errors", "evaluation.json missing tier B (cross-level holdout)")
        else:
            tier_b = tiers["B"]
            macro_b = tier_b.get("macro_avg", {})
            report["checks"]["tier_b_macro_avg"] = macro_b
            tier_a_macro = tiers.get("A", {}).get("macro_avg", {})
            for model_name, scores_b in macro_b.items():
                auc_b = scores_b.get("test_auc")
                if auc_b is None:
                    add_issue(
                        issues,
                        "errors",
                        f"Tier B {model_name}: missing test_auc in macro_avg",
                    )
                elif auc_b >= 0.999:
                    auc_a = tier_a_macro.get(model_name, {}).get("test_auc")
                    if auc_a is not None and auc_a >= 0.999:
                        add_issue(
                            issues,
                            "warnings",
                            f"Tier A and B both perfect for {model_name} "
                            f"(A={auc_a}, B={auc_b}) — still suspicious",
                        )
                elif auc_b < 0.5:
                    add_issue(
                        issues,
                        "warnings",
                        f"Tier B {model_name}: weak test_auc={auc_b} (below random)",
                    )
            if tier_a_macro and macro_b:
                for model_name, scores_a in tier_a_macro.items():
                    auc_a = scores_a.get("test_auc")
                    auc_b = macro_b.get(model_name, {}).get("test_auc")
                    if (
                        auc_a is not None
                        and auc_b is not None
                        and auc_a >= 0.99
                        and auc_b < 0.99
                    ):
                        add_issue(
                            issues,
                            "warnings",
                            f"{model_name}: tier A inflated ({auc_a:.3f}) vs tier B realistic ({auc_b:.3f})",
                        )
    elif "evaluation.json" not in report["checks"]:
        pass  # already reported missing in required_json loop

    report["issues"] = issues
    report["summary"] = {
        "errors": len(issues.get("errors", [])),
        "warnings": len(issues.get("warnings", [])),
    }
    return report


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)

    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        run_dir = find_latest_run(artifacts_dir)

    if not run_dir.is_dir():
        print(f"Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    report = verify_run(run_dir)
    out_path = run_dir / "verification_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Verification report: {out_path}")
    print(json.dumps(report["summary"], indent=2))

    for severity in ("errors", "warnings"):
        for msg in report.get("issues", {}).get(severity, []):
            print(f"[{severity.upper()}] {msg}")

    if report["summary"]["errors"] > 0:
        sys.exit(1)
    if args.fail_on_warnings and report["summary"]["warnings"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
