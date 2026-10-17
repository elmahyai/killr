"""Local libcurl symbol table from the R package sysdata."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_SYMBOL_DATA_PATH = Path(__file__).with_name("symbol_data.json")


@lru_cache(maxsize=1)
def _symbol_table() -> tuple[dict[str, object], ...]:
    with _SYMBOL_DATA_PATH.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    return tuple(rows)


def curl_symbols(filter: str = "") -> list[dict[str, object]]:
    pattern = re.compile(filter, re.IGNORECASE)
    return [dict(row) for row in _symbol_table() if pattern.search(row["name"])]
