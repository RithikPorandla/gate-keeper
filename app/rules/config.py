from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_RULES_YAML = Path(__file__).with_name("rules.yaml")
# Repo root = three levels up from this file (app/rules/config.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache
def load_rules_config() -> dict[str, Any]:
    with _RULES_YAML.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache
def load_watchlist() -> frozenset[str]:
    """Load the synthetic watchlist of names (lower-cased for matching).

    NOTE: entirely fictional data shipped for demo purposes only.
    """
    cfg = load_rules_config()
    rel = cfg["watchlist"]["source_file"]
    path = _REPO_ROOT / rel
    names: set[str] = set()
    if not path.exists():
        return frozenset()
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("name") or "").strip().lower()
            if name:
                names.add(name)
    return frozenset(names)
