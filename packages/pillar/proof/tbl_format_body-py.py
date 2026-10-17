import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from pillar.format_tbl import tbl_format_body, tbl_format_setup


def one():
    frame = DataFrame({"a": [1, 2, 3], "b": ["x", "yy", "zzz"], "c": [True, False, None]})
    setup = tbl_format_setup(frame, width=30, n=2)
    return "\n".join(tbl_format_body(frame, setup))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
