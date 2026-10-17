import json
import statistics
import time

from progressr.external import with_progress_shiny
from progressr.options import ProgressrError


def one():
    try:
        with_progress_shiny(lambda: 1 + 1)
    except ProgressrError as exc:
        return str(exc)
    raise AssertionError("with_progress_shiny(lambda: 1 + 1) did not error")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"message": value, "median_ms": statistics.median(elapsed)}))
