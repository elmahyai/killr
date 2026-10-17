import json
import math
import os
import statistics
import tempfile
import time

from rjsonio import readJSONStream
from rjsonio.values import Atomic, AsIs, Matrix, RList


def _piece(kind, values, names):
    label = {
        "integer": "integer/integer",
        "numeric": "numeric/double",
        "logical": "logical/logical",
        "character": "character/character",
    }[kind]
    parts = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            parts.append("NA")
        elif isinstance(value, bool):
            parts.append("TRUE" if value else "FALSE")
        elif isinstance(value, float) and value.is_integer():
            parts.append(str(int(value)))
        else:
            parts.append(str(value))
    names_text = "" if names is None else " names=" + ",".join(names)
    return f"{label}[{','.join(parts)}]{names_text}"


def show(value):
    if value is None:
        return "NULL"
    if isinstance(value, AsIs):
        shown = show(value.value)
        if shown.endswith(" class=list"):
            return shown[: -len(" class=list")] + " class=AsIs"
        return shown + " class=AsIs"
    if isinstance(value, Matrix):
        kind = {
            "integer": "integer",
            "numeric": "double",
            "logical": "logical",
            "character": "character",
        }[value.kind]
        parts = []
        for item in value.data:
            if item is None or (isinstance(item, float) and math.isnan(item)):
                parts.append("NA")
            elif isinstance(item, bool):
                parts.append("TRUE" if item else "FALSE")
            elif isinstance(item, float) and item.is_integer():
                parts.append(str(int(item)))
            else:
                parts.append(str(item))
        return f"matrix/{kind}[{value.nrow}x{value.ncol}:{','.join(parts)}]"
    if isinstance(value, Atomic):
        return _piece(value.kind, value.values, value.names)
    if isinstance(value, RList):
        inner = " | ".join(show(item) for item in value.values)
        if value.names is None:
            names_text = " nonames"
        else:
            names_text = " names=" + ",".join(value.names)
        return f"LIST{{{inner}}}{names_text} class=list"
    if isinstance(value, list):
        inner = " | ".join(show(item) for item in value)
        return f"LIST{{{inner}}} nonames class=list"
    if isinstance(value, bool):
        return f"logical/logical[{'TRUE' if value else 'FALSE'}]"
    if isinstance(value, int):
        return f"integer/integer[{value}]"
    if isinstance(value, float):
        text = str(int(value)) if value.is_integer() else str(value)
        return f"numeric/double[{text}]"
    if isinstance(value, str):
        return f"character/character[{value}]"
    return repr(value)


def stream_file(text: str):
    with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
        handle.write(text.encode("utf-8"))
        path = handle.name
    try:
        return readJSONStream(path)
    finally:
        os.unlink(path)


def one():
    parts = [
        show(stream_file("[1, 2, 3]")),
        show(stream_file('[1,2,3]{"a":[true,false]}')),
    ]
    with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
        handle.write(b'[1,2,3]{"a":[true,false]}')
        path = handle.name
    try:
        parts.append(show(readJSONStream(path, cb=lambda x: len(x))))
    finally:
        os.unlink(path)
    return "\n".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
