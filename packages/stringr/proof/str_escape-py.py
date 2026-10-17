import json
import statistics
import time
from pathlib import Path

from rlang import Named
from stringi._na import NA
from stringr.escape import str_escape

Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_escape-python.txt").write_text(
    "str_escape(\".\") returns " + str_escape(".")[0] + ".\n"
)

piece = ["a.b", "(x)", NA, "", "\\", "a^b$", ".^$\\|*+?{}[]()"]


def plain(value):
    if value is NA:
        return None
    if isinstance(value, Named):
        return {"data": [plain(item) for item in value], "names": list(value.names)}
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def one():
    return {
        "main": str_escape(piece * 20),
        "dot": str_escape("."),
        "many": str_escape(["a.b", "(x)", NA, "", "\\", "a^b$"]),
        "all": str_escape(".^$\\|*+?{}[]()"),
        "names": str_escape(Named([".", "?"], ["a", "b"])),
        "empty": str_escape([]),
        "null": str_escape(None),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": plain(value), "median_ms": statistics.median(elapsed)}))
