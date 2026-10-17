"""The modelr teaching tables, plus mtcars and iris for the examples."""

from __future__ import annotations

import json
from pathlib import Path

from modelr.frame import Factor, Frame

_DATA = Path(__file__).resolve().parent / "data"


def _load(name):
    payload = json.loads((_DATA / f"{name}.json").read_text(encoding="utf-8"))
    columns = {}
    for column, spec in payload["columns"].items():
        kind = spec["type"]
        values = spec["values"]
        if kind == "factor":
            columns[column] = Factor(values, spec["levels"], ordered=False)
        elif kind == "ordered":
            columns[column] = Factor(values, spec["levels"], ordered=True)
        elif kind == "integer":
            columns[column] = [None if value is None else int(value) for value in values]
        elif kind == "double":
            columns[column] = [None if value is None else float(value) for value in values]
        elif kind == "logical":
            columns[column] = values
        else:
            columns[column] = values
    return Frame(columns)


heights = _load("heights")
sim1 = _load("sim1")
sim2 = _load("sim2")
sim3 = _load("sim3")
sim4 = _load("sim4")
mtcars = _load("mtcars")
iris = _load("iris")
