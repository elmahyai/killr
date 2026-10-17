import json
import statistics
import time
from datetime import date, datetime

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Environment, List, Matrix, Table
from pillar.summary import obj_sum


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
        List([1, 2]),
        NULL,
        Environment(),
        Table((4, 2, 2, 2)),
    ]
    values = []
    shorts = []
    for item in items:
        result = obj_sum(item)
        values.append(str(result))
        shorts.append(getattr(result, "short", None))
    return {"value": values, "short": shorts}


packed = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "value": packed["value"],
    "short": packed["short"],
    "median_ms": statistics.median(elapsed),
}, ensure_ascii=False))
