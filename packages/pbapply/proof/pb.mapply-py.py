import json
import statistics
import time

from pbapply.mapply import pb_mapply
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        return list(pb_mapply(lambda x, y: x + y, [[1, 2, 3], [4, 5, 6]], MoreArgs=None))
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
