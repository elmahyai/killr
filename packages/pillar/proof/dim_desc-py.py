import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Matrix, Table
from pillar.summary import dim_desc


def one():
    trees = DataFrame({name: list(range(31)) for name in ("Girth", "Height", "Volume")})
    return [
        dim_desc(list(range(1, 11))),
        dim_desc(Table((4, 2, 2, 2))),
        dim_desc(NULL),
        dim_desc(trees),
        dim_desc(Matrix(list(range(1, 5)), 2)),
        dim_desc(list(range(1, 1001))),
        dim_desc(DataFrame({"a": [1]})),
        dim_desc(Matrix(list(range(1, 11)), 10)),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
