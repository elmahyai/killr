import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from lifecycle import LifecycleError
from pillar.colonnade import squeeze


def one():
    try:
        squeeze()
    except LifecycleError as exc:
        return str(exc)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
