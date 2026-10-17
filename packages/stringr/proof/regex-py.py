import json
import statistics
import time
from pathlib import Path

from stringi._na import is_na
from stringr.pattern import regex

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "regex-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'regex("[a-z]+", ignore_case = TRUE) stores case_insensitive TRUE.\n',
    encoding="utf-8",
)


def atom(value):
    if is_na(value):
        return None
    if value is True or value is False:
        return bool(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    raise TypeError(type(value))


def pack(obj):
    return {
        "kind": obj.kind,
        "pattern": [None if is_na(value) else value for value in obj],
        "options": [[key, atom(value)] for key, value in obj.options.items()],
    }


def one():
    return [
        pack(regex("a.b")),
        pack(regex("[a-z]+", True)),
        pack(regex("a", True, True, True, True)),
        pack(regex("a", time_limit=10)),
        pack(regex("a", dot_all=True)),
        pack(regex("a", dotall=True, dot_all=False)),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
