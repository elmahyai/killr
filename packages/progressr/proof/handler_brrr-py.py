import json
import statistics
import time

from progressr.external import handler_brrr
from progressr.options import ProgressrError


def one():
    try:
        handler_brrr()
    except ProgressrError as exc:
        return str(exc)
    raise AssertionError("handler_brrr() did not error")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"message": value, "median_ms": statistics.median(elapsed)}))
