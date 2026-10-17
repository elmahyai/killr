import json
import statistics
import time

from progressr.bars import handler_winprogressbar
from progressr.options import ProgressrError


def one():
    try:
        handler_winprogressbar(enable=True, inputs={"title": "nope"})
    except ProgressrError as exc:
        return {"error": str(exc)}
    return {"error": ""}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
