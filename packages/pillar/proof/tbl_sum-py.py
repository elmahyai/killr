import json
import statistics
import time
from datetime import date, datetime

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import DataFrame, Matrix
from pillar.summary import tbl_sum


def mean(values):
    return values


def one():
    items = [
        list(range(1, 11)),
        Matrix(list(range(1, 11)), 10),
        DataFrame({"a": [1]}),
        date.today(),
        datetime.now(),
        mean,
    ]
    values = []
    names = []
    shorts = []
    for item in items:
        result = tbl_sum(item)
        values.append(str(result))
        names.append(result.name)
        shorts.append(getattr(result, "short", None))
    return {"value": values, "name": names, "short": shorts}


packed = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "value": packed["value"],
    "name": packed["name"],
    "short": packed["short"],
    "median_ms": statistics.median(elapsed),
}, ensure_ascii=False))
