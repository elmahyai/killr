import json
import statistics
import time
from pathlib import Path

from stringi._na import NA

from stringr.case import str_to_kebab


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


Path("/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_to_kebab-python.txt").write_text(repr(str_to_kebab("MyVariable")) + "\n", encoding="utf-8")


def one():
    return {
        "basic": str_to_kebab("MyVariable"),
        "vec": str_to_kebab(["myVariable", "1MyVariable1", "testABCTest", "IlÉtaitUneFois", NA, ""]),
        "empty": str_to_kebab([])
    }


value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
