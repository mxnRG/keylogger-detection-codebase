#!/usr/bin/env python3
"""
ML inference API for live telemetry rows (FYP demo).

POST /predict — score one feature row against per-level ensembles.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUN = PROJECT_ROOT / "artifacts" / "run_20260529_193015"
RUN_DIR = Path(os.environ.get("FYP_ARTIFACT_RUN", str(DEFAULT_RUN)))
MANIFEST_PATH = RUN_DIR / "ensemble_manifest.json"

THRESHOLD = float(os.environ.get("FYP_ML_THRESHOLD", "0.5"))
MALICIOUS_STREAK = int(os.environ.get("FYP_ML_MALICIOUS_STREAK", "3"))
BENIGN_STREAK = int(os.environ.get("FYP_ML_BENIGN_STREAK", "3"))

SKIP_COLUMNS = {
    "timestamp", "label", "hour", "minute", "second",
    "scenario", "collector_type", "source_file", "os", "level",
    "split_group", "session_id", "capture_group",
}

_malicious_streak = 0
_benign_streak = 0
_last_label = "benign"

app = FastAPI(title="FYP ML Inference API", version="1.0.0")


class PredictRequest(BaseModel):
    features: Dict[str, Any] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    label: str
    level: Optional[int] = None
    confidence: float
    per_level: Dict[str, float]
    raw_label: str


class EnsembleLevel:
    def __init__(self, level: int, config: dict):
        self.level = level
        self.features: List[str] = list(config["features"])
        self.models = []
        for entry in config["models"]:
            path = Path(entry["path"])
            if not path.is_file():
                path = RUN_DIR / path.name
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
                preds = model.predict(X)
                probs.append(float(preds[0]))
        return float(np.mean(probs)) if probs else 0.0


_ensembles: Dict[int, EnsembleLevel] = {}


def _load_ensembles() -> None:
    global _ensembles
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing ensemble manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text())
    per_level = manifest.get("per_level", {})
    _ensembles = {}
    for key, cfg in per_level.items():
        level = int(key)
        _ensembles[level] = EnsembleLevel(level, cfg)


@app.on_event("startup")
def startup() -> None:
    _load_ensembles()


def _apply_hysteresis(raw_malicious: bool) -> str:
    global _malicious_streak, _benign_streak, _last_label
    if raw_malicious:
        _malicious_streak += 1
        _benign_streak = 0
    else:
        _benign_streak += 1
        _malicious_streak = 0

    if _malicious_streak >= MALICIOUS_STREAK:
        _last_label = "malicious"
    elif _benign_streak >= BENIGN_STREAK:
        _last_label = "benign"
    return _last_label


def _normalize_row(body: PredictRequest) -> Dict[str, Any]:
    row = dict(body.features)
    return row


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "run_dir": str(RUN_DIR),
        "levels": sorted(_ensembles.keys()),
        "threshold": THRESHOLD,
    }


@app.get("/schema")
def schema() -> dict:
    all_features = set()
    for ens in _ensembles.values():
        all_features.update(ens.features)
    return {
        "feature_columns": sorted(all_features),
        "per_level_features": {str(k): v.features for k, v in _ensembles.items()},
        "skip_columns": sorted(SKIP_COLUMNS),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    if not _ensembles:
        raise HTTPException(status_code=503, detail="Models not loaded")

    row = _normalize_row(body)
    per_level_scores: Dict[str, float] = {}
    best_level: Optional[int] = None
    best_score = 0.0

    for level, ens in sorted(_ensembles.items()):
        score = ens.score(row)
        per_level_scores[str(level)] = round(score, 4)
        if score > best_score:
            best_score = score
            best_level = level

    raw_malicious = best_score >= THRESHOLD
    label = _apply_hysteresis(raw_malicious)
    reported_level = best_level if label == "malicious" else None

    return PredictResponse(
        label=label,
        level=reported_level,
        confidence=round(best_score, 4),
        per_level=per_level_scores,
        raw_label="malicious" if raw_malicious else "benign",
    )


def main():
    import uvicorn

    host = os.environ.get("FYP_ML_API_HOST", "127.0.0.1")
    port = int(os.environ.get("FYP_ML_API_PORT", "8765"))
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
