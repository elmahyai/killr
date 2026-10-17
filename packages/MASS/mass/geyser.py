"""The MASS geyser dataset: waiting time and eruption duration."""

from __future__ import annotations

import csv
from pathlib import Path


def _load() -> dict[str, list[float]]:
    path = Path(__file__).with_name("geyser.csv")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        "waiting": [float(row["waiting"]) for row in rows],
        "duration": [float(row["duration"]) for row in rows],
    }


geyser = _load()
