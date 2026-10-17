import json
import statistics
import time
from pathlib import Path

from stringi._na import NA


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value



import math

from stringi.sprintf import stri_sprintf

example = stri_sprintf("%s=%d", "a", 1e5)[0]
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_sprintf-python.txt").write_text(
    f"stri_sprintf('%s=%d', 'a', 1e5) returns {example}.\n"
)


def one():
    return {
        "s": stri_sprintf("%s", "hello"),
        "d": stri_sprintf("%d", 3),
        "f": stri_sprintf("%f", 1.5),
        "na": stri_sprintf("%s", NA),
        "nan": stri_sprintf("%f", float("nan")),
        "inf": stri_sprintf("%f", float("inf")),
        "ninf": stri_sprintf("%f", float("-inf")),
        "sci": stri_sprintf("%s", [1e5, 1e-4]),
        "a": stri_sprintf("%a", 1.5),
        "A": stri_sprintf("%A", 1.5),
        "g": stri_sprintf("%g", 1e6),
        "width": stri_sprintf("[%10s]", ["abcd", "ąĆ"]),
        "star": stri_sprintf("%1$#- *2$.*3$f", 1.23456, 10, 3),
        "pi": stri_sprintf(["%s", "%f"], math.pi),
        "hex": stri_sprintf("%#x", 255),
        "negx": stri_sprintf("%x", -1),
        "zero": stri_sprintf("%+f", [-0.0, 0.0]),
        "bulk": stri_sprintf("%s=%d", ["a", "b"] * 400, [1, 2] * 400),
    }

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
