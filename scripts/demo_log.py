"""Shared demo logging helpers (FYP_DEMO_VERBOSE=1)."""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional


def demo_verbose() -> bool:
    return os.environ.get("FYP_DEMO_VERBOSE", "").lower() in ("1", "true", "yes")


def deep_log_enabled() -> bool:
    return os.environ.get("FYP_ML_DEEP_LOG", "1").lower() in ("1", "true", "yes")


def setup_demo_logger(name: str, tag: str, log_file: Optional[str] = None) -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log

    level = logging.DEBUG if demo_verbose() else logging.INFO
    log.setLevel(level)
    fmt = logging.Formatter(
        f"[%(asctime)s] [{tag}] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    log.addHandler(stream)

    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)

    log.propagate = False
    return log
