import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from pillar.glimpse import format_glimpse


def one():
    items = List([[1, 2, 3], "A, B", Factor(["A", "B, C"]), [], NULL])
    return "\n".join(format_glimpse(items))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
