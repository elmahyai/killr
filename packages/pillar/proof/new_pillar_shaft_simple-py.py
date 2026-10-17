import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from pillar.shaft import new_pillar_shaft_simple
from pillar._layout import lines_of


def one():
    shaft = new_pillar_shaft_simple(["ab", None, "cdef"], width=6, align="left")
    return "\n".join(lines_of(shaft.format(width=4)))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
