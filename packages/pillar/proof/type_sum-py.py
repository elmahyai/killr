import json
import statistics
import time
from datetime import date, datetime

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Environment, Factor, List, Matrix, Table
from pillar.summary import type_sum


def mean(values):
    return values


def one():
    return [
        type_sum(Factor(["a", "b", "c"])),
        type_sum(Factor(["a", "b", "c"], ordered=True)),
        type_sum(list(range(1, 11))),
        type_sum(1.5),
        type_sum(True),
        type_sum("a"),
        type_sum(1 + 2j),
        type_sum(b"\x01"),
        type_sum(DataFrame({"a": [1]})),
        type_sum(Matrix(list(range(1, 5)), 2)),
        type_sum(Table((4, 2, 2, 2))),
        type_sum(date.today()),
        type_sum(datetime.now()),
        type_sum(List([1, 2])),
        type_sum(mean),
        type_sum(Environment()),
        type_sum(NULL),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
