import json
import statistics
import time
import warnings
from pathlib import Path

from stringi._na import NA, is_na
from stringr.pattern import fixed

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "fixed-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    'fixed("a.b", ignore_case = TRUE) stores case_insensitive TRUE.\n',
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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return [
            pack(fixed("a.b")),
            pack(fixed("a.b", True)),
            pack(fixed(["abb", "a.b"])),
            pack(fixed(NA)),
            pack(fixed(True)),
            pack(fixed(False)),
            pack(fixed(None)),
            pack(fixed([])),
        ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, separators=(",", ":")))
