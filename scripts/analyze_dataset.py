#!/usr/bin/env python3
"""Read-only dataset analysis: separators, split feasibility, feature recommendations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import yaml

# Shared with train_ml.py (keep in sync)
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

LABEL_MAP = {"benign": 0, "malicious": 1, "attack": 1, "keylogger": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze telemetry dataset for ML readiness")
    parser.add_argument(
        "--data-dir",
        default=str(Path(__file__).resolve().parent.parent / "dataset"),
        help="Dataset root containing manifest.yaml",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "docs" / "DATASET_ANALYSIS_LATEST.md"),
        help="Output markdown report path",
    )
    return parser.parse_args()


def load_manifest(data_dir: Path) -> dict:
    with open(data_dir / "manifest.yaml", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, on_bad_lines="skip")


def is_separator(benign: pd.Series, malicious: pd.Series) -> bool:
    b = pd.to_numeric(benign, errors="coerce").dropna()
    m = pd.to_numeric(malicious, errors="coerce").dropna()
    if len(b) == 0 or len(m) == 0:
        return False
    return bool(b.max() < m.min() or m.max() < b.min())


def analyze_level_pair(
    level: int,
    benign_path: Path,
    malicious_path: Path,
) -> Dict[str, object]:
    db = read_csv(benign_path)
    dm = read_csv(malicious_path)
    numeric_cols = [
        c
        for c in db.columns
        if c in dm.columns
        and pd.api.types.is_numeric_dtype(db[c])
        and c not in ("label",)
    ]

    separators: List[str] = []
    overlap_rows: List[str] = []
    for col in sorted(numeric_cols):
        b = pd.to_numeric(db[col], errors="coerce")
        m = pd.to_numeric(dm[col], errors="coerce")
        if is_separator(b, m):
            separators.append(col)
            overlap_rows.append(
                f"| `{col}` | {b.min():.4g}–{b.max():.4g} | {m.min():.4g}–{m.max():.4g} | yes |"
            )
        else:
            overlap_rows.append(
                f"| `{col}` | {b.min():.4g}–{b.max():.4g} | {m.min():.4g}–{m.max():.4g} | no |"
            )

    return {
        "level": level,
        "benign_file": benign_path.name,
        "malicious_file": malicious_path.name,
        "benign_rows": len(db),
        "malicious_rows": len(dm),
        "separators": separators,
        "overlap_table": overlap_rows,
    }


def build_report(data_dir: Path) -> str:
    manifest = load_manifest(data_dir)
    archive_root = data_dir / manifest["archive_root"]
    train_levels = manifest.get("train_levels", [2, 3, 4])
    levels_cfg = manifest.get("levels", {})
    capture_groups = manifest.get("capture_groups", {})

    lines = [
        "# Dataset Analysis (Latest)",
        "",
        f"Generated from manifest at `{data_dir / 'manifest.yaml'}`.",
        "",
        "## Summary",
        "",
        f"- Training levels: {train_levels}",
        f"- Archive root: `{manifest['archive_root']}`",
        f"- Files per level: 1 benign + 1 malicious (no leave-one-file-out with both classes in train and test)",
        "",
        "## Per-Level Feature Separation",
        "",
    ]

    all_separators: Dict[int, List[str]] = {}
    for level in train_levels:
        level_key = str(level)
        entry = levels_cfg.get(level_key) or levels_cfg.get(level)
        if not entry:
            continue
        benign_rel = entry["benign"][0]
        malicious_rel = entry["malicious"][0]
        benign_path = archive_root / benign_rel
        malicious_path = archive_root / malicious_rel
        if not benign_path.exists() or not malicious_path.exists():
            lines.append(f"### Level {level} — MISSING FILES")
            continue

        info = analyze_level_pair(level, benign_path, malicious_path)
        all_separators[level] = info["separators"]  # type: ignore[assignment]

        bg_key = f"L{level}_benign"
        mal_key = f"L{level}_malicious"
        bg_group = capture_groups.get(bg_key, "unknown")
        mal_group = capture_groups.get(mal_key, "unknown")

        lines.extend([
            f"### Level {level}",
            "",
            f"- Benign: `{info['benign_file']}` ({info['benign_rows']:,} rows) — capture group `{bg_group}`",
            f"- Malicious: `{info['malicious_file']}` ({info['malicious_rows']:,} rows) — capture group `{mal_group}`",
            f"- Perfect separators: {info['separators'] or '(none detected)'}",
            "",
            "| Feature | Benign range | Malicious range | Perfect separator |",
            "|---------|--------------|-----------------|-------------------|",
        ])
        lines.extend(info["overlap_table"])  # type: ignore[arg-type]
        lines.append("")

    lines.extend([
        "## Split Feasibility",
        "",
        "| Strategy | Feasible? | Notes |",
        "|----------|-----------|-------|",
        "| Row-level stratified split | yes | Upper-bound metric; same capture files in train and test → optimistic AUC |",
        "| Leave-one-file-out | no | One benign + one malicious file per level; holdout leaves single class |",
        "| Cross-level holdout | yes | **Primary thesis metric** — train 2 levels, test held-out level |",
        "| Session-aware group split | limited | Only 2 `split_group` values per level → falls back to row split |",
        "",
        "## Recommended Feature Drops",
        "",
        "### Environment fingerprint blocklist (always exclude for tier C)",
        "",
        "```",
        ", ".join(ENV_FINGERPRINT_DROP),
        "```",
        "",
        "### Per-level perfect separators (also exclude for honest eval)",
        "",
    ])

    for level, seps in all_separators.items():
        lines.append(f"- **L{level}:** {seps or '(none)'}")

    lines.extend([
        "",
        "### Behavioral feature set (tier C training)",
        "",
        "```",
        ", ".join(BEHAVIORAL_FEATURES),
        "```",
        "",
        "## Evaluation Tiers",
        "",
        "| Tier | Split | Feature policy | Purpose |",
        "|------|-------|----------------|---------|",
        "| A | Per-level row stratified | Standard + leakage drops | In-distribution upper bound |",
        "| B | Cross-level holdout | Standard + leakage drops | **Primary thesis metric** |",
        "| C | Cross-level or per-level | Behavioral-only + env strip | Signal beyond VM fingerprints |",
        "",
        "## Commands",
        "",
        "```bash",
        "python scripts/analyze_dataset.py --data-dir dataset",
        "python scripts/train_ml.py --split-mode all --feature-policy standard",
        "python scripts/verify_artifacts.py",
        "```",
    ])

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(data_dir)
    out_path.write_text(report, encoding="utf-8")
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
