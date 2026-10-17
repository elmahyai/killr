import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from pillar.format_tbl import tbl_nrow


def one():
    frame = DataFrame({"a": [1, 2, 3], "b": ["x", "yy", "zzz"], "c": [True, False, None]})
    return tbl_nrow(frame)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
