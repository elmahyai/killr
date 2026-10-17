"""fromJSON and parse_json. Record arrays become data frames when simplifying."""

from __future__ import annotations

import json
from typing import Any

from jsonlite._values import NA, DataFrame


def fromJSON(txt: str, *, simplify_vector: bool = True, flatten: bool = False) -> Any:
    """Parse JSON. Arrays of records become a data frame when ``simplify_vector`` is true."""

    if not isinstance(txt, str):
        raise TypeError("Argument 'txt' must be a JSON string, URL or file.")
    value = json.loads(txt)
    if not simplify_vector:
        return _plain(value)
    simplified = _simplify(value)
    if flatten and isinstance(simplified, DataFrame):
        from jsonlite._frames import flatten as flatten_frame

        return flatten_frame(simplified)
    return simplified


def parse_json(json_text: str, *, simplify_vector: bool = False, flatten: bool = False) -> Any:
    """Parse JSON text. Unlike fromJSON, vectors stay lists unless asked."""

    return fromJSON(json_text, simplify_vector=simplify_vector, flatten=flatten)


def _plain(value: Any) -> Any:
    if value is None:
        return NA
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


def _simplify(value: Any) -> Any:
    if isinstance(value, list):
        items = [_simplify(item) for item in value]
        if items and all(isinstance(item, dict) for item in items):
            return _records_to_frame(items)
        return items
    if isinstance(value, dict):
        return {key: _simplify(item) for key, item in value.items()}
    if value is None:
        return NA
    return value


def _records_to_frame(records: list[dict]) -> DataFrame:
    names: list[str] = []
    for record in records:
        for key in record:
            if key not in names:
                names.append(key)
    columns: dict[str, list] = {name: [] for name in names}
    for record in records:
        for name in names:
            columns[name].append(record[name] if name in record else NA)
    return DataFrame(columns)
