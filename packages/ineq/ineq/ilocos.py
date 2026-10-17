"""The ineq Ilocos household table."""

from __future__ import annotations

import csv
from pathlib import Path


_NUMERIC = {
    "income",
    "family.size",
    "AP.income",
    "AP.family.size",
    "AP.weight",
}


def _load() -> dict[str, list]:
    path = Path(__file__).with_name("ilocos.csv")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = {name: [] for name in rows[0]}
    for row in rows:
        for name, value in row.items():
            if name in _NUMERIC:
                columns[name].append(float(value) if value != "" else None)
            else:
                columns[name].append(value if value != "" else None)
    return columns


Ilocos = _load()
