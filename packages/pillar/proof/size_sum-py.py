import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import DataFrame, Table
from pillar.summary import size_sum


def mean(values):
    return values


def one():
    trees = DataFrame({name: list(range(31)) for name in ("Girth", "Height", "Volume")})
    return [
        size_sum(list(range(1, 11))),
        size_sum(trees),
        size_sum(Table((4, 2, 2, 2))),
        size_sum(1),
        size_sum(mean),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
