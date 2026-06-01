"""
Load deployed ML artifact metadata and evaluation metrics for the GUI.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN = PROJECT_ROOT / "artifacts" / "run_20260531_l2_hybrid"
FALLBACK_EVAL_RUN = PROJECT_ROOT / "artifacts" / "run_20260529_193015"


def get_run_dir() -> Path:
    return Path(os.environ.get("FYP_ARTIFACT_RUN", str(DEFAULT_RUN)))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _tier_b_has_metrics(evaluation: Optional[Dict[str, Any]]) -> bool:
    if not evaluation:
        return False
    tier_key = evaluation.get("thesis_primary") or evaluation.get("evaluation_primary_tier") or "B"
    tier = (evaluation.get("tiers") or {}).get(tier_key) or {}
    return bool(tier.get("macro_avg") or tier.get("folds"))


def _evaluation_candidates(run_dir: Path, manifest: Dict[str, Any]) -> List[Path]:
    seen: set[str] = set()
    candidates: List[Path] = []

    def add(path: Path) -> None:
        key = str(path.resolve())
        if key not in seen and path.is_file():
            seen.add(key)
            candidates.append(path)

    add(run_dir / "evaluation.json")
    notes = manifest.get("notes", "") or ""
    for run_id in re.findall(r"run_\d+_\d+", notes):
        add(PROJECT_ROOT / "artifacts" / run_id / "evaluation.json")
    add(FALLBACK_EVAL_RUN / "evaluation.json")
    return candidates


def _resolve_evaluation_path(run_dir: Path, manifest: Dict[str, Any]) -> Tuple[Optional[Path], Optional[str]]:
    """Prefer an evaluation.json that includes tier-B cross-level metrics."""
    best: Optional[Path] = None
    for candidate in _evaluation_candidates(run_dir, manifest):
        evaluation = _read_json(candidate)
        if _tier_b_has_metrics(evaluation):
            return candidate, candidate.parent.name
        if best is None:
            best = candidate

    if best is not None:
        return best, best.parent.name
    return None, None


def _ensemble_level_auc_ap(level_cfg: Dict[str, Any]) -> Tuple[float, float]:
    models = level_cfg.get("models") or []
    if not models:
        return 0.0, 0.0
    aucs = [float(m.get("test_auc", 0)) for m in models]
    aps = [float(m.get("test_ap", 0)) for m in models]
    return sum(aucs) / len(aucs), sum(aps) / len(aps)


def _tier_b_summary(evaluation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not evaluation:
        return {}
    tier_key = evaluation.get("thesis_primary") or evaluation.get("evaluation_primary_tier") or "B"
    tier = (evaluation.get("tiers") or {}).get(tier_key) or {}
    macro = tier.get("macro_avg") or {}
    if not macro:
        return {"tier": tier_key, "name": tier.get("name", ""), "ensemble_auc": 0.0, "ensemble_ap": 0.0, "per_model": {}}

    per_model = {}
    aucs: List[float] = []
    aps: List[float] = []
    for name, stats in macro.items():
        ta = float(stats.get("test_auc", 0))
        tp = float(stats.get("test_ap", 0))
        per_model[name.replace("_", " ").title()] = {"test_auc": ta, "test_ap": tp}
        aucs.append(ta)
        aps.append(tp)

    folds = []
    for fold in tier.get("folds") or []:
        test_level = fold.get("test_level")
        models = fold.get("models") or {}
        fold_aucs = [float(m.get("test_auc", 0)) for m in models.values()]
        fold_aps = [float(m.get("test_ap", 0)) for m in models.values()]
        folds.append(
            {
                "test_level": test_level,
                "train_levels": fold.get("train_levels"),
                "test_rows": fold.get("test_rows"),
                "ensemble_auc": sum(fold_aucs) / len(fold_aucs) if fold_aucs else 0.0,
                "ensemble_ap": sum(fold_aps) / len(fold_aps) if fold_aps else 0.0,
            }
        )

    return {
        "tier": tier_key,
        "name": tier.get("name", "cross_level_holdout"),
        "description": tier.get("description", "Cross-level holdout (thesis primary)"),
        "ensemble_auc": sum(aucs) / len(aucs) if aucs else 0.0,
        "ensemble_ap": sum(aps) / len(aps) if aps else 0.0,
        "per_model": per_model,
        "folds": folds,
    }


def load_ml_insights() -> Dict[str, Any]:
    """Return manifest, per-level deployed metrics, and tier-B evaluation summary."""
    run_dir = get_run_dir()
    manifest = _read_json(run_dir / "ensemble_manifest.json") or {}
    eval_path, eval_run_id = _resolve_evaluation_path(run_dir, manifest)
    evaluation = _read_json(eval_path) if eval_path else None

    per_level: List[Dict[str, Any]] = []
    for level_key in sorted((manifest.get("per_level") or {}).keys(), key=lambda x: int(x)):
        cfg = manifest["per_level"][level_key]
        auc, ap = _ensemble_level_auc_ap(cfg)
        model_names = [m.get("model", "?") for m in (cfg.get("models") or [])]
        per_level.append(
            {
                "level": int(level_key),
                "feature_count": len(cfg.get("features") or []),
                "models": model_names,
                "ensemble_auc": auc,
                "ensemble_ap": ap,
            }
        )

    return {
        "run_dir": str(run_dir),
        "run_id": manifest.get("run_id") or run_dir.name,
        "strategy": manifest.get("strategy", "per_level_average"),
        "notes": manifest.get("notes", ""),
        "evaluation_run_id": eval_run_id,
        "evaluation_path": str(eval_path) if eval_path else None,
        "per_level": per_level,
        "tier_b": _tier_b_summary(evaluation),
        "manifest_ok": bool(manifest),
        "evaluation_ok": evaluation is not None,
    }
