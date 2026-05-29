#!/usr/bin/env python3
"""
Train ML models on telemetry datasets and save artifacts (AUC curves, PR curves,
confusion matrices, and metrics) to /artifacts.
"""

import argparse
import json
import re
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
import matplotlib
import joblib
from xgboost import XGBClassifier

matplotlib.use("Agg")
import matplotlib.pyplot as plt


LABEL_MAP = {
    "benign": 0,
    "malicious": 1,
    "attack": 1,
    "keylogger": 1,
}

CORE_FEATURES = [
    "keyboard_events",
    "keyboard_to_process_ratio",
    "cpu_to_keyboard_ratio",
    "kernel_context_switches_delta",
    "kernel_sys_read_delta",
    "kernel_sys_write_delta",
    "total_open_files",
    "network_connections",
    "total_connections",
    "process_count",
    "active_processes",
    "background_processes",
    "total_threads",
]

CONTEXT_FEATURES = [
    "suspicious_process_names",
    "shell_processes",
    "python_processes",
    "thread_to_process_ratio",
]

ALLOWED_FEATURES = CORE_FEATURES + CONTEXT_FEATURES
BEHAVIOR_FEATURES = [
    "keyboard_events",
    "keyboard_to_process_ratio",
    "cpu_to_keyboard_ratio",
    "kernel_context_switches_delta",
    "kernel_sys_read_delta",
    "kernel_sys_write_delta",
    "network_connections",
    "total_connections",
    "suspicious_process_names",
    "shell_processes",
    "python_processes",
    "thread_to_process_ratio",
]
MODEL_FEATURES = BEHAVIOR_FEATURES
MIN_REQUIRED_FEATURES = 5
L2_SEPARATOR_FEATURES = [
    "keyboard_events",
    "total_open_files",
    "process_count",
    "active_processes",
    "background_processes",
]
GLOBAL_LEAKAGE_DROP = ["keyboard_events", "cpu_threads"]

ENV_FINGERPRINT_DROP = [
    "swap_memory",
    "disk_usage_percent",
    "system_uptime_minutes",
    "process_count",
    "active_processes",
    "background_processes",
    "total_open_files",
    "users_logged_in",
    "keyboard_events",
    "keyboard_to_process_ratio",
    "cpu_threads",
    "hour",
    "minute",
    "second",
]

BEHAVIORAL_FEATURES = [
    "kernel_context_switches_delta",
    "kernel_sys_read_delta",
    "kernel_sys_write_delta",
    "kernel_openat_delta",
    "kernel_execve_delta",
    "kernel_connect_delta",
    "keyboard_hardware_interrupts",
    "cpu_to_keyboard_ratio",
    "thread_to_process_ratio",
    "network_connections",
    "total_connections",
    "shell_processes",
    "python_processes",
    "suspicious_process_names",
    "high_cpu_processes",
    "high_memory_processes",
    "zombie_processes",
    "cpu_usage",
    "memory_usage",
    "total_threads",
]

LEVEL_FEATURE_CANDIDATES: Dict[int, List[str]] = {
    2: [
        "cpu_usage",
        "memory_usage",
        "swap_memory",
        "disk_usage_percent",
        "system_uptime_minutes",
        "high_cpu_processes",
        "high_memory_processes",
        "zombie_processes",
        "total_threads",
        "thread_to_process_ratio",
        "cpu_to_keyboard_ratio",
        "keyboard_hardware_interrupts",
        "kernel_context_switches_delta",
        "kernel_sys_read_delta",
        "kernel_sys_write_delta",
        "network_connections",
        "total_connections",
        "shell_processes",
        "python_processes",
        "suspicious_process_names",
        "keyboard_to_process_ratio",
        "total_open_files",
        "process_count",
        "active_processes",
        "background_processes",
    ],
    3: [
        "cpu_usage",
        "memory_usage",
        "swap_memory",
        "disk_usage_percent",
        "system_uptime_minutes",
        "high_cpu_processes",
        "high_memory_processes",
        "zombie_processes",
        "total_threads",
        "thread_to_process_ratio",
        "cpu_to_keyboard_ratio",
        "keyboard_hardware_interrupts",
        "kernel_context_switches_delta",
        "kernel_sys_read_delta",
        "kernel_sys_write_delta",
        "kernel_openat_delta",
        "kernel_execve_delta",
        "kernel_connect_delta",
        "network_connections",
        "total_connections",
        "shell_processes",
        "python_processes",
        "suspicious_process_names",
        "keyboard_to_process_ratio",
        "total_open_files",
        "process_count",
        "active_processes",
        "background_processes",
    ],
    4: [],  # same as L3
}

LEVEL_FEATURE_CANDIDATES[4] = list(LEVEL_FEATURE_CANDIDATES[3])

TRAIN_LEVELS_DEFAULT = [2, 3, 4]


@dataclass
class DatasetBundle:
    features: pd.DataFrame
    labels: pd.Series
    metadata: pd.DataFrame


@dataclass
class IngestionResult:
    data: pd.DataFrame
    cleaning_summary: List[Dict[str, object]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train telemetry ML models and store artifacts in /artifacts"
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent.parent / "dataset"),
        help="Directory containing telemetry CSV files",
    )
    parser.add_argument(
        "--include-kaggle",
        action="store_true",
        help="Include Kaggle dataset if present",
    )
    parser.add_argument(
        "--kaggle-path",
        default=str(Path(__file__).resolve().parent.parent / "dataset" / "KAGGLE" / "archive" / "Keylogger_Detection.csv"),
        help="Path to Kaggle dataset CSV",
    )
    parser.add_argument(
        "--artifacts-dir",
        default=str(Path(__file__).resolve().parent.parent / "artifacts"),
        help="Directory to store artifacts",
    )
    parser.add_argument(
        "--label-col",
        default="label",
        help="Label column name in telemetry CSVs",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split fraction (used if no level-based split)",
    )
    parser.add_argument(
        "--val-size",
        type=float,
        default=0.2,
        help="Validation split fraction (used if no level-based split)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for splits",
    )
    parser.add_argument(
        "--split-mode",
        choices=["per_level", "cross_level", "all"],
        default="all",
        help="Evaluation split: per_level (tier A), cross_level (tier B/C), or all",
    )
    parser.add_argument(
        "--feature-policy",
        choices=["standard", "behavioral"],
        default="standard",
        help="Feature set for cross-level eval; behavioral = tier C blocklist",
    )
    return parser.parse_args()


def infer_level(filename: str) -> Optional[int]:
    match = re.search(r"level(\d+)", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"L(\d+)", filename)
    if match:
        return int(match.group(1))
    return None


def infer_os(filename: str) -> str:
    lower = filename.lower()
    if "windows" in lower:
        return "windows"
    return "linux"


def normalize_label(value: str) -> Optional[int]:
    if value is None:
        return None
    key = str(value).strip().lower()
    return LABEL_MAP.get(key)


def read_csv_clean(path: Path) -> Tuple[pd.DataFrame, Dict[str, object]]:
    raw = path.read_bytes()
    had_nul = b"\x00" in raw
    if had_nul:
        raw = raw.replace(b"\x00", b"")

    line_count = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
    data_lines = max(0, line_count - 1)

    try:
        df = pd.read_csv(BytesIO(raw), on_bad_lines="skip")
    except Exception as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc

    summary = {
        "file": path.name,
        "rows_loaded": int(len(df)),
        "data_lines": int(data_lines),
        "rows_dropped": int(max(0, data_lines - len(df))),
        "nul_bytes_stripped": bool(had_nul),
    }

    return df, summary


def load_csv(
    path: Path,
    label_col: str,
    level: Optional[int] = None,
    capture_group: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    df, summary = read_csv_clean(path)

    df["source_file"] = path.name
    df["session_id"] = path.name
    if capture_group:
        df["capture_group"] = capture_group
    df["os"] = infer_os(path.name)
    if level is None:
        level = infer_level(path.name)
    df["level"] = level if level is not None else "unknown"
    summary["path"] = str(path)

    if label_col in df.columns:
        df[label_col] = df[label_col].apply(normalize_label)
    else:
        raise ValueError(f"Missing label column '{label_col}' in {path}")

    return df, summary


def load_manifest(data_dir: Path) -> Dict[str, object]:
    manifest_path = data_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install PyYAML: pip install PyYAML") from exc

    with open(manifest_path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def collect_datasets_from_manifest(
    data_dir: Path,
    label_col: str,
) -> Tuple[IngestionResult, Dict[str, object]]:
    manifest = load_manifest(data_dir)
    archive_root = data_dir / manifest["archive_root"]
    train_levels = manifest.get("train_levels", TRAIN_LEVELS_DEFAULT)
    levels_cfg = manifest.get("levels", {})
    capture_groups = manifest.get("capture_groups", {})

    data_frames: List[pd.DataFrame] = []
    cleaning_summary: List[Dict[str, object]] = []
    files_loaded: List[str] = []
    files_skipped: List[str] = []

    for level in train_levels:
        level_key = str(level)
        level_entry = levels_cfg.get(level_key) or levels_cfg.get(level)
        if not level_entry:
            files_skipped.append(f"level_{level_key}:not_in_manifest")
            continue

        for class_name in ("benign", "malicious"):
            for rel_path in level_entry.get(class_name, []):
                csv_path = archive_root / rel_path
                if not csv_path.exists():
                    files_skipped.append(f"{csv_path}:missing")
                    continue
                group_key = f"L{level}_{class_name}"
                capture_group = capture_groups.get(group_key)
                df, summary = load_csv(
                    csv_path,
                    label_col,
                    level=int(level),
                    capture_group=capture_group,
                )
                summary["manifest_class"] = class_name
                summary["manifest_level"] = int(level)
                data_frames.append(df)
                cleaning_summary.append(summary)
                files_loaded.append(str(csv_path.relative_to(data_dir)))

    if not data_frames:
        raise RuntimeError(
            f"No CSV datasets loaded from manifest under {archive_root}"
        )

    data = pd.concat(data_frames, ignore_index=True)
    ingestion_meta = {
        "archive_root": str(archive_root),
        "files_loaded": files_loaded,
        "files_skipped": files_skipped,
        "train_levels": train_levels,
    }
    return IngestionResult(data=data, cleaning_summary=cleaning_summary), ingestion_meta


def load_kaggle(path: Path, label_col: str) -> Tuple[pd.DataFrame, Dict[str, object]]:
    df = pd.read_csv(path)
    summary = {
        "file": path.name,
        "rows_loaded": int(len(df)),
        "data_lines": int(len(df)),
        "rows_dropped": 0,
        "nul_bytes_stripped": False,
    }
    df["source_file"] = path.name
    df["os"] = "kaggle"
    df["level"] = "kaggle"

    if label_col in df.columns:
        df[label_col] = df[label_col].apply(normalize_label)
    else:
        raise ValueError(f"Missing label column '{label_col}' in {path}")

    return df, summary


def collect_datasets(data_dir: Path, label_col: str, include_kaggle: bool, kaggle_path: Path) -> IngestionResult:
    csv_files = sorted(data_dir.glob("*.csv"))
    data_frames: List[pd.DataFrame] = []
    cleaning_summary: List[Dict[str, object]] = []

    for csv_path in csv_files:
        if csv_path.name == "L2_Combined.csv":
            continue
        if infer_os(csv_path.name) != "linux":
            continue
        df, summary = load_csv(csv_path, label_col)
        data_frames.append(df)
        cleaning_summary.append(summary)

    if include_kaggle and kaggle_path.exists():
        df, summary = load_kaggle(kaggle_path, label_col)
        data_frames.append(df)
        cleaning_summary.append(summary)

    if not data_frames:
        raise RuntimeError(f"No CSV datasets found in {data_dir}")

    data = pd.concat(data_frames, ignore_index=True)
    data = data[data["os"] == "linux"].copy()
    return IngestionResult(data=data, cleaning_summary=cleaning_summary)


def align_schema(df: pd.DataFrame, label_col: str, allowed_features: List[str]) -> DatasetBundle:
    df = df.copy()

    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' missing")

    labels = df[label_col]
    metadata_cols = ["source_file", "os", "level", "split_group", "session_id", "capture_group"]
    metadata_cols = [col for col in metadata_cols if col in df.columns]
    metadata = df[metadata_cols]

    drop_cols = set(metadata_cols + [label_col])
    non_feature_cols = [col for col in df.columns if col in drop_cols]
    features = df.drop(columns=non_feature_cols, errors="ignore")

    for col in allowed_features:
        if col not in features.columns:
            features[col] = 0
        features[col] = pd.to_numeric(features[col], errors="coerce")

    numeric_features = features[allowed_features].replace([np.inf, -np.inf], np.nan)
    numeric_features = numeric_features.fillna(0)

    return DatasetBundle(features=numeric_features, labels=labels, metadata=metadata)


def split_by_level(bundle: DatasetBundle, random_state: int, val_size: float, test_size: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict[str, List[int]]]:
    levels = bundle.metadata["level"].unique().tolist()
    level_numbers = [lvl for lvl in levels if isinstance(lvl, int)]

    if len(level_numbers) >= 3:
        level_numbers.sort()
        test_level = level_numbers[-1]
        val_level = level_numbers[-2]
        train_levels = level_numbers[:-2]

        train_mask = bundle.metadata["level"].isin(train_levels)
        val_mask = bundle.metadata["level"] == val_level
        test_mask = bundle.metadata["level"] == test_level

        split_info = {
            "train_levels": train_levels,
            "val_level": [val_level],
            "test_level": [test_level],
        }

        return (
            bundle.features[train_mask].values,
            bundle.features[val_mask].values,
            bundle.features[test_mask].values,
            bundle.labels[train_mask].values,
            bundle.labels[val_mask].values,
            bundle.labels[test_mask].values,
            split_info,
        )

    # Fallback to stratified random split
    X = bundle.features.values
    y = bundle.labels.values

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=(val_size + test_size), random_state=random_state, stratify=y
    )
    relative_val = val_size / (val_size + test_size)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=(1 - relative_val), random_state=random_state, stratify=y_temp
    )

    split_info = {
        "train_levels": ["random"],
        "val_level": ["random"],
        "test_level": ["random"],
    }

    return X_train, X_val, X_test, y_train, y_val, y_test, split_info


def evaluate_model(
    name: str,
    model,
    X_val,
    y_val,
    X_test,
    y_test,
    out_dir: Path,
    plot_subtitle: str = "",
) -> Dict[str, float]:
    y_val_scores = model.predict_proba(X_val)[:, 1]
    y_test_scores = model.predict_proba(X_test)[:, 1]

    metrics = {
        "val_auc": roc_auc_score(y_val, y_val_scores),
        "test_auc": roc_auc_score(y_test, y_test_scores),
        "val_ap": average_precision_score(y_val, y_val_scores),
        "test_ap": average_precision_score(y_test, y_test_scores),
        "in_distribution_auc": roc_auc_score(y_test, y_test_scores),
    }

    title_suffix = f"\n{plot_subtitle}" if plot_subtitle else ""

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_test_scores)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, label=f"ROC AUC = {metrics['test_auc']:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(f"{name} ROC Curve{title_suffix}")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_dir / f"{name}_roc_curve.png")
    plt.close()

    # PR curve
    precision, recall, _ = precision_recall_curve(y_test, y_test_scores)
    plt.figure(figsize=(6, 5))
    plt.plot(recall, precision, label=f"AP = {metrics['test_ap']:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(f"{name} Precision-Recall Curve{title_suffix}")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(out_dir / f"{name}_pr_curve.png")
    plt.close()

    # Confusion matrix
    y_pred = (y_test_scores >= 0.5).astype(int)
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(cmap="Blues")
    plt.title(f"{name} Confusion Matrix{title_suffix}")
    plt.tight_layout()
    plt.savefig(out_dir / f"{name}_confusion_matrix.png")
    plt.close()

    return metrics


def validate_dataset(df: pd.DataFrame, label_col: str, allowed_features: List[str]) -> Dict[str, object]:
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' missing")

    if df.empty:
        raise RuntimeError("Dataset is empty after ingestion")

    label_counts = df[label_col].value_counts(dropna=True).to_dict()
    if len(label_counts) < 2:
        raise RuntimeError("Dataset contains only one class after label normalization")

    present_features = [col for col in allowed_features if col in df.columns]
    if len(present_features) < MIN_REQUIRED_FEATURES:
        raise RuntimeError(
            f"Too few usable features after filtering ({len(present_features)} found, {MIN_REQUIRED_FEATURES} required)"
        )

    return {
        "rows": int(len(df)),
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "levels": df["level"].value_counts(dropna=False).to_dict(),
        "os_counts": df["os"].value_counts(dropna=False).to_dict(),
        "present_features": present_features,
        "missing_features": [col for col in allowed_features if col not in df.columns],
    }


def build_quality_report(
    df: pd.DataFrame,
    bundle: DatasetBundle,
    label_col: str,
    allowed_features: List[str],
    cleaning_summary: List[Dict[str, object]],
) -> Dict[str, object]:
    missingness = {}
    for col in allowed_features:
        if col in df.columns:
            missingness[col] = float(df[col].isna().mean())
        else:
            missingness[col] = 1.0

    outliers = {}
    for col in bundle.features.columns:
        series = bundle.features[col]
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            outliers[col] = {"count": 0, "fraction": 0.0}
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        outliers[col] = {
            "count": count,
            "fraction": float(count / max(len(series), 1)),
        }

    return {
        "rows": int(len(df)),
        "label_counts": df[label_col].value_counts(dropna=True).to_dict(),
        "level_counts": df["level"].value_counts(dropna=False).to_dict(),
        "os_counts": df["os"].value_counts(dropna=False).to_dict(),
        "missingness": missingness,
        "outliers": outliers,
        "cleaning_summary": cleaning_summary,
    }


def build_models(random_state: int, scale_pos_weight: float) -> Dict[str, object]:
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            random_state=random_state,
            class_weight="balanced",
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=300,
            random_state=random_state,
            class_weight="balanced",
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=random_state,
            scale_pos_weight=scale_pos_weight,
            n_jobs=-1,
        ),
    }


def compute_leakage_safe_features(
    df: pd.DataFrame,
    label_col: str,
    candidate_features: List[str],
    forced_drop: Optional[List[str]] = None,
) -> Tuple[List[str], Dict[str, List[str]]]:
    forced_drop = forced_drop or []
    allowed = []
    dropped = {}

    labels = df[label_col].values if label_col in df.columns else None
    for feature in candidate_features:
        if feature in forced_drop:
            dropped[feature] = ["forced_drop"]
            continue

        series = pd.to_numeric(df.get(feature), errors="coerce")
        if series is None:
            allowed.append(feature)
            continue

        reasons = []
        non_null = series.dropna()
        if non_null.nunique(dropna=True) <= 1:
            reasons.append("constant")

        if labels is not None:
            label_series = pd.Series(labels, index=series.index)
            if non_null.isin([0, 1]).all():
                if series.fillna(0).astype(int).equals(label_series.astype(int)):
                    reasons.append("matches_label")

            b = series[label_series == 0].dropna()
            m = series[label_series == 1].dropna()
            if len(b) and len(m):
                if b.max() < m.min() or m.max() < b.min():
                    reasons.append("single_threshold_separator")

        if reasons:
            dropped[feature] = reasons
        else:
            allowed.append(feature)

    return allowed, dropped


def build_feature_dive(
    df: pd.DataFrame,
    label_col: str,
    candidate_features: List[str],
) -> Dict[str, object]:
    report = {
        "files": {},
        "overall": {},
    }

    def summarize_frame(frame: pd.DataFrame) -> Dict[str, object]:
        summary = {
            "rows": int(len(frame)),
            "columns": int(len(frame.columns)),
            "label_counts": frame[label_col].value_counts(dropna=True).to_dict()
            if label_col in frame.columns
            else "missing",
        }

        numeric_cols = frame.select_dtypes(include=["number"]).columns.tolist()
        summary["numeric_cols"] = numeric_cols

        constants = []
        for col in numeric_cols:
            if frame[col].nunique(dropna=True) <= 1:
                constants.append(col)
        summary["constant_cols"] = constants

        summary["missingness"] = {
            col: float(frame[col].isna().mean()) for col in numeric_cols
        }

        if numeric_cols:
            summary["duplicate_numeric_row_rate"] = float(
                frame[numeric_cols].duplicated().mean()
            )
        else:
            summary["duplicate_numeric_row_rate"] = None

        leakage_flags = []
        if label_col in frame.columns:
            labels = frame[label_col].values
            for col in numeric_cols:
                series = frame[col]
                if series.dropna().isin([0, 1]).all():
                    if series.fillna(0).astype(int).equals(pd.Series(labels).astype(int)):
                        leakage_flags.append({"feature": col, "reason": "matches_label"})

                b = series[labels == 0].dropna()
                m = series[labels == 1].dropna()
                if len(b) and len(m):
                    if b.max() < m.min() or m.max() < b.min():
                        leakage_flags.append(
                            {"feature": col, "reason": "single_threshold_separator"}
                        )

        summary["leakage_flags"] = leakage_flags
        summary["missing_features"] = [
            feature for feature in candidate_features if feature not in frame.columns
        ]
        summary["extra_features"] = [
            col
            for col in frame.columns
            if col not in candidate_features + [label_col, "timestamp", "hour", "minute", "second"]
        ]
        return summary

    if "source_file" in df.columns:
        for name, frame in df.groupby("source_file"):
            report["files"][name] = summarize_frame(frame)

    report["overall"] = summarize_frame(df)
    return report


def build_split_group(df: pd.DataFrame) -> pd.Series:
    for col in ["session_id", "run_id", "capture_id"]:
        if col in df.columns:
            return df[col].astype(str).fillna("unknown")

    if "timestamp" in df.columns:
        timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
        date_key = timestamps.dt.strftime("%Y%m%d").fillna("unknown")
        return df["source_file"].astype(str) + "_" + date_key

    return df["source_file"].astype(str)


def resolve_candidate_features(
    train_levels: List[int],
    feature_policy: str,
) -> List[str]:
    if feature_policy == "behavioral":
        return list(BEHAVIORAL_FEATURES)
    return sorted(
        {feat for lvl in train_levels for feat in LEVEL_FEATURE_CANDIDATES.get(int(lvl), [])}
    )


def resolve_forced_drop(feature_policy: str) -> List[str]:
    forced = list(GLOBAL_LEAKAGE_DROP)
    if feature_policy == "behavioral":
        forced.extend(ENV_FINGERPRINT_DROP)
    return list(dict.fromkeys(forced))


def prepare_level_features(
    df: pd.DataFrame,
    label_col: str,
    level_tag: str,
    candidate_features: List[str],
    feature_policy: str,
) -> Tuple[List[str], Dict[str, List[str]]]:
    forced_drop = resolve_forced_drop(feature_policy)
    effective, leakage_drops = compute_leakage_safe_features(
        df,
        label_col,
        candidate_features,
        forced_drop=forced_drop,
    )
    if str(level_tag) == "2" and feature_policy != "behavioral":
        effective = [f for f in effective if f not in L2_SEPARATOR_FEATURES]
        for feature in L2_SEPARATOR_FEATURES:
            leakage_drops.setdefault(feature, []).append("l2_separator_drop")
    return effective, leakage_drops


def macro_average_model_metrics(folds: List[Dict[str, object]]) -> Dict[str, Dict[str, float]]:
    totals: Dict[str, Dict[str, List[float]]] = {}
    for fold in folds:
        for model_name, model_metrics in fold.get("models", {}).items():
            totals.setdefault(model_name, {})
            for key in ("test_auc", "test_ap", "val_auc", "val_ap"):
                val = model_metrics.get(key)
                if val is not None:
                    totals[model_name].setdefault(key, []).append(float(val))
    macro: Dict[str, Dict[str, float]] = {}
    for model_name, values in totals.items():
        macro[model_name] = {
            key: float(np.mean(scores)) for key, scores in values.items() if scores
        }
    return macro


def cross_level_eval(
    df: pd.DataFrame,
    args: argparse.Namespace,
    train_levels: List[int],
    run_dir: Path,
    feature_policy: str,
    tier_tag: str,
) -> Dict[str, object]:
    """Train on two levels, test on held-out level (tier B or C)."""
    candidates = resolve_candidate_features(train_levels, feature_policy)

    effective, _ = prepare_level_features(
        df,
        args.label_col,
        "pooled",
        candidates,
        feature_policy,
    )
    if not effective:
        raise RuntimeError(f"No features available for cross-level eval ({tier_tag})")

    tier_dir = run_dir / f"cross_level_{tier_tag}"
    tier_dir.mkdir(parents=True, exist_ok=True)

    folds: List[Dict[str, object]] = []
    numeric_levels = sorted(int(lvl) for lvl in train_levels)

    for test_level in numeric_levels:
        train_mask = df["level"] != test_level
        test_mask = df["level"] == test_level
        train_df = df[train_mask].copy()
        test_df = df[test_mask].copy()

        if train_df[args.label_col].nunique() < 2 or test_df[args.label_col].nunique() < 2:
            continue

        effective, leakage_drops = prepare_level_features(
            df,
            args.label_col,
            "pooled",
            candidates,
            feature_policy,
        )
        forced_drop = resolve_forced_drop(feature_policy)
        bundle = align_schema(df, args.label_col, effective)
        train_idx = train_df.index
        test_idx = test_df.index

        X_train = bundle.features.loc[train_idx].values
        y_train = bundle.labels.loc[train_idx].values
        X_test = bundle.features.loc[test_idx].values
        y_test = bundle.labels.loc[test_idx].values

        holdout = args.val_size
        if len(y_train) > 10 and len(set(y_train.tolist())) >= 2:
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_train,
                y_train,
                test_size=holdout,
                random_state=args.random_state,
                stratify=y_train,
            )
        else:
            X_tr, y_tr = X_train, y_train
            X_val, y_val = X_test, y_test

        pos = max(int((y_tr == 1).sum()), 1)
        neg = max(int((y_tr == 0).sum()), 1)
        scale_pos_weight = float(neg / pos)
        models = build_models(args.random_state, scale_pos_weight)

        train_level_list = [lvl for lvl in numeric_levels if lvl != test_level]
        fold_report: Dict[str, object] = {
            "train_levels": train_level_list,
            "test_level": test_level,
            "train_rows": int(len(y_tr)),
            "test_rows": int(len(y_test)),
            "features": effective,
            "feature_drops": leakage_drops,
            "models": {},
        }

        fold_dir = tier_dir / f"test_L{test_level}"
        fold_dir.mkdir(parents=True, exist_ok=True)

        for name, model in models.items():
            model.fit(X_tr, y_tr)
            model_dir = fold_dir / name
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"{name}.joblib"
            joblib.dump(model, model_path)
            subtitle = f"Cross-level: train L{train_level_list} → test L{test_level}"
            metrics = evaluate_model(
                name,
                model,
                X_val,
                y_val,
                X_test,
                y_test,
                model_dir,
                plot_subtitle=subtitle,
            )
            metrics["model_path"] = str(model_path)
            fold_report["models"][name] = metrics

        folds.append(fold_report)

    macro_avg = macro_average_model_metrics(folds)
    return {
        "name": "cross_level_holdout" if tier_tag == "B" else "behavioral_cross_level",
        "feature_policy": feature_policy,
        "forced_drop": forced_drop,
        "folds": folds,
        "macro_avg": macro_avg,
    }


def build_tier_a_summary(report: Dict[str, object]) -> Dict[str, object]:
    levels = report.get("levels", {})
    per_level: Dict[str, object] = {}
    model_scores: Dict[str, Dict[str, List[float]]] = {}

    for level_key, level_report in levels.items():
        level_models = {}
        for model_name, metrics in level_report.get("models", {}).items():
            level_models[model_name] = {
                "in_distribution_auc": metrics.get("test_auc"),
                "in_distribution_ap": metrics.get("test_ap"),
                "val_auc": metrics.get("val_auc"),
                "val_ap": metrics.get("val_ap"),
            }
            for key in ("test_auc", "test_ap"):
                val = metrics.get(key)
                if val is not None:
                    model_scores.setdefault(model_name, {}).setdefault(key, []).append(float(val))
        per_level[level_key] = {
            "split_method": level_report.get("split", {}).get("split_method"),
            "models": level_models,
        }

    macro_avg = {
        model: {k: float(np.mean(v)) for k, v in scores.items()}
        for model, scores in model_scores.items()
    }

    return {
        "name": "in_distribution_row_split",
        "description": "Upper bound — same capture sessions in train and test",
        "levels": per_level,
        "macro_avg": macro_avg,
    }


def train_level(
    df: pd.DataFrame,
    level_tag: str,
    run_dir: Path,
    args: argparse.Namespace,
    allowed_features: List[str],
    feature_policy: str = "standard",
) -> Dict[str, object]:
    effective_features, leakage_drops = prepare_level_features(
        df,
        args.label_col,
        level_tag,
        allowed_features,
        feature_policy,
    )

    bundle = align_schema(df, args.label_col, effective_features)
    combined = bundle.features.copy()
    combined[args.label_col] = bundle.labels.values
    combined = combined.drop_duplicates()
    deduped_features = combined.drop(columns=[args.label_col])
    deduped_labels = combined[args.label_col]

    split_method = "group"
    X_train = X_val = X_test = None
    y_train = y_val = y_test = None

    groups = bundle.metadata.loc[combined.index, "split_group"].fillna("unknown")
    unique_groups = groups.unique()

    # Two capture files (one benign, one malicious) cannot be split by group
    # without single-class test sets — use stratified row splits instead.
    if len(unique_groups) <= 2:
        holdout = args.test_size + args.val_size
        X_train, X_temp, y_train, y_temp = train_test_split(
            deduped_features.values,
            deduped_labels.values,
            test_size=holdout,
            random_state=args.random_state,
            stratify=deduped_labels.values,
        )
        relative_test = args.test_size / max(holdout, 1e-6)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp,
            y_temp,
            test_size=relative_test,
            random_state=args.random_state,
            stratify=y_temp,
        )
        split_method = "stratified_row_split"
    elif len(unique_groups) >= 2:
        gss = GroupShuffleSplit(
            n_splits=1, test_size=args.test_size, random_state=args.random_state
        )
        train_val_idx, test_idx = next(gss.split(deduped_features, deduped_labels, groups))

        X_test = deduped_features.iloc[test_idx].values
        y_test = deduped_labels.iloc[test_idx].values

        if len(unique_groups) >= 3:
            remaining_groups = groups.iloc[train_val_idx]
            relative_val_size = args.val_size / max(1.0 - args.test_size, 1e-6)
            gss_val = GroupShuffleSplit(
                n_splits=1, test_size=relative_val_size, random_state=args.random_state
            )
            train_idx, val_idx = next(
                gss_val.split(
                    deduped_features.iloc[train_val_idx],
                    deduped_labels.iloc[train_val_idx],
                    remaining_groups,
                )
            )
            X_train = deduped_features.iloc[train_val_idx].iloc[train_idx].values
            y_train = deduped_labels.iloc[train_val_idx].iloc[train_idx].values
            X_val = deduped_features.iloc[train_val_idx].iloc[val_idx].values
            y_val = deduped_labels.iloc[train_val_idx].iloc[val_idx].values
        else:
            X_train, X_val, y_train, y_val = train_test_split(
                deduped_features.iloc[train_val_idx].values,
                deduped_labels.iloc[train_val_idx].values,
                test_size=args.val_size,
                random_state=args.random_state,
                stratify=deduped_labels.iloc[train_val_idx].values,
            )
            split_method = "group_test_stratified_val"

    if X_train is None or len(set(y_train.tolist())) < 2 or len(set(y_val.tolist())) < 2:
        holdout = args.test_size + args.val_size
        X_train, X_temp, y_train, y_temp = train_test_split(
            deduped_features.values,
            deduped_labels.values,
            test_size=holdout,
            random_state=args.random_state,
            stratify=deduped_labels.values,
        )
        relative_test = args.test_size / max(holdout, 1e-6)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp,
            y_temp,
            test_size=relative_test,
            random_state=args.random_state,
            stratify=y_temp,
        )
        split_method = "stratified_fallback"

    test_equals_val = False
    if X_test is not None and X_val is not None:
        test_equals_val = bool(
            np.array_equal(X_test, X_val) and np.array_equal(y_test, y_val)
        )

    split_info = {
        "train_levels": ["random"],
        "val_level": ["random"],
        "test_level": ["random"],
        "deduped_rows": int(len(deduped_features)),
        "original_rows": int(len(bundle.features)),
        "deduped": True,
        "split_method": split_method,
        "train_rows": int(len(y_train)) if y_train is not None else 0,
        "val_rows": int(len(y_val)) if y_val is not None else 0,
        "test_rows": int(len(y_test)) if y_test is not None else 0,
        "test_equals_val": test_equals_val,
    }

    pos = max(int((y_train == 1).sum()), 1)
    neg = max(int((y_train == 0).sum()), 1)
    scale_pos_weight = float(neg / pos)

    models = build_models(args.random_state, scale_pos_weight)
    report = {
        "level": level_tag,
        "rows": int(len(df)),
        "features": list(bundle.features.columns),
        "split": split_info,
        "feature_drops": leakage_drops,
        "models": {},
    }

    features_path = run_dir / "features.json"
    with open(features_path, "w") as handle:
        json.dump(list(bundle.features.columns), handle, indent=2)

    for name, model in models.items():
        model.fit(X_train, y_train)
        model_dir = run_dir / name
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / f"{name}.joblib"
        joblib.dump(model, model_path)
        metrics = evaluate_model(
            name,
            model,
            X_val,
            y_val,
            X_test,
            y_test,
            model_dir,
            plot_subtitle="Upper bound — same capture sessions in train and test",
        )
        metrics["model_path"] = str(model_path)
        report["models"][name] = metrics

    report["features_path"] = str(features_path)
    return report


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    ingestion, ingestion_meta = collect_datasets_from_manifest(data_dir, args.label_col)
    df = ingestion.data

    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    df = df[df[args.label_col].notna()].copy()
    df["split_group"] = build_split_group(df)

    manifest = load_manifest(data_dir)
    train_levels = manifest.get("train_levels", TRAIN_LEVELS_DEFAULT)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = artifacts_dir / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    all_candidates = sorted(
        {feat for lvl in train_levels for feat in LEVEL_FEATURE_CANDIDATES.get(int(lvl), [])}
    )
    quality_bundle = align_schema(df, args.label_col, all_candidates)
    quality_report = build_quality_report(
        df,
        quality_bundle,
        args.label_col,
        all_candidates,
        ingestion.cleaning_summary,
    )

    feature_dive = build_feature_dive(df, args.label_col, all_candidates)

    report = {
        "run_id": run_id,
        "rows": int(len(df)),
        "ingestion": ingestion_meta,
        "split_mode": args.split_mode,
        "feature_policy": args.feature_policy,
        "levels": {},
    }

    per_level_manifest: Dict[str, object] = {}
    run_per_level = args.split_mode in ("per_level", "all")

    if run_per_level:
        for level in train_levels:
            level = int(level)
            level_df = df[df["level"] == level].copy()
            if level_df.empty:
                continue

            if level_df[args.label_col].nunique() < 2:
                raise RuntimeError(f"Level {level} has only one class after ingestion")

            candidates = LEVEL_FEATURE_CANDIDATES.get(level, MODEL_FEATURES)
            level_dir = run_dir / f"level_{level}"
            level_dir.mkdir(parents=True, exist_ok=True)
            level_report = train_level(
                level_df,
                str(level),
                level_dir,
                args,
                candidates,
                feature_policy="standard",
            )
            report["levels"][str(level)] = level_report

            models_entries = []
            for model_name, metrics in level_report["models"].items():
                models_entries.append(
                    {
                        "model": model_name,
                        "path": metrics["model_path"],
                        "test_auc": metrics.get("test_auc"),
                        "test_ap": metrics.get("test_ap"),
                    }
                )

            per_level_manifest[str(level)] = {
                "strategy": "average",
                "features": level_report["features"],
                "features_path": level_report.get("features_path"),
                "models": models_entries,
                "weights": [1.0 / max(len(models_entries), 1)] * len(models_entries),
            }

    if run_per_level and not report["levels"]:
        raise RuntimeError("No levels were trained; check manifest and CSV paths")

    evaluation: Dict[str, object] = {
        "thesis_primary": "B",
        "split_mode": args.split_mode,
        "feature_policy": args.feature_policy,
        "tiers": {},
    }

    if run_per_level:
        evaluation["tiers"]["A"] = build_tier_a_summary(report)

    run_cross = args.split_mode in ("cross_level", "all")
    if run_cross:
        tier_b = cross_level_eval(
            df,
            args,
            train_levels,
            run_dir,
            feature_policy="standard",
            tier_tag="B",
        )
        evaluation["tiers"]["B"] = tier_b

        tier_c = cross_level_eval(
            df,
            args,
            train_levels,
            run_dir,
            feature_policy="behavioral",
            tier_tag="C",
        )
        evaluation["tiers"]["C"] = tier_c

    ensemble_manifest = {
        "run_id": run_id,
        "strategy": "per_level_average",
        "per_level": per_level_manifest,
        "evaluation_primary_tier": "B",
    }

    with open(run_dir / "metrics.json", "w") as f:
        json.dump(report, f, indent=2)

    with open(run_dir / "dataset_quality.json", "w") as f:
        json.dump(quality_report, f, indent=2)

    with open(run_dir / "feature_dive.json", "w") as f:
        json.dump(feature_dive, f, indent=2)

    with open(run_dir / "ensemble_manifest.json", "w") as f:
        json.dump(ensemble_manifest, f, indent=2)

    with open(run_dir / "evaluation.json", "w") as f:
        json.dump(evaluation, f, indent=2)

    print(f"Artifacts saved to {run_dir}")
    if "B" in evaluation.get("tiers", {}):
        macro = evaluation["tiers"]["B"].get("macro_avg", {})
        for model, scores in macro.items():
            auc = scores.get("test_auc")
            if auc is not None:
                print(f"  Tier B macro {model}: test_auc={auc:.4f}")


if __name__ == "__main__":
    main()
