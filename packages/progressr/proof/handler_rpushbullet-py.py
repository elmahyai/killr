import json
import statistics
import time

from progressr.external import handler_rpushbullet
from progressr.options import ProgressrError


def one():
    try:
        handler_rpushbullet()
    except ProgressrError as exc:
        return str(exc)
    raise AssertionError("handler_rpushbullet() did not error")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"message": value, "median_ms": statistics.median(elapsed)}))
