"""MASS data sets, copied from the R package by proof/export-datasets-r.R.

Each data set is ``mass/data/<name>.csv`` (the table) and ``mass/data/<name>.json``
(kind, column types, factor levels, row names, time-series attributes).

Access a data set as ``mass.datasets.<name>`` (loaded on first use) or with
``load(name)``. Return shapes:

- data frame: dict of column name -> list (floats for numeric and integer,
  strings for factor and character, bools for logical; NA is nan or None).
- numeric vector: list of floats.
- time series: dict with ``tsp`` (start, end, frequency) and ``values``.
- list of numeric vectors: dict of name -> list of floats.

Factor level order is in ``factor_levels(name)``. Row names that are not the
default 1..n are in ``row_names(name)``.
"""

from __future__ import annotations

import csv
import json
import math
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).with_name("data")
NAMES: tuple[str, ...] = tuple(sorted(p.stem for p in _DIR.glob("*.json")))
_NAME_SET = frozenset(NAMES)


@lru_cache(maxsize=None)
def _meta(name: str) -> dict:
    return json.loads((_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _parse(text: str | None, kind: str):
    if kind in ("numeric", "integer"):
        if text is None or text == "NA":
            return math.nan
        return float(text)
    if kind == "logical":
        if text is None or text == "NA":
            return None
        return text == "TRUE"
    # factor and character
    if text is None or text == "NA":
        return None
    return text


def load(name: str):
    """Return data set ``name`` in the shape described in the module docstring."""
    if name not in _NAME_SET:
        raise KeyError(f"no MASS data set named {name!r}")
    meta = _meta(name)
    with (_DIR / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    header, body = rows[0], rows[1:]
    types = {c["name"]: c["type"] for c in meta["columns"]}
    columns = {
        col: [_parse(row[j] if j < len(row) else None, types[col]) for row in body]
        for j, col in enumerate(header)
    }
    kind = meta["kind"]
    if kind == "data.frame":
        return columns
    if kind == "numeric":
        return columns["value"]
    if kind == "ts":
        start, end, frequency = (float(v) for v in meta["tsp"])
        return {"tsp": (start, end, frequency), "values": columns["value"]}
    if kind == "list":
        return columns
    raise ValueError(f"unknown kind {kind!r} for {name}")


def factor_levels(name: str) -> dict[str, list[str]]:
    """Return factor level order for each factor column of data set ``name``."""
    return {
        c["name"]: list(c["levels"])
        for c in _meta(name)["columns"]
        if c["type"] == "factor"
    }


def row_names(name: str) -> list[str] | None:
    """Return non-default row names of data set ``name``, or None when they are 1..n."""
    names = _meta(name).get("rownames")
    return None if names is None else list(names)


def __getattr__(name: str):
    if name in _NAME_SET:
        value = load(name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _NAME_SET)
