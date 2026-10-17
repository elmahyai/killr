import json
import statistics
import time

from pbapply.pbtapply import pbtapply
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        x = list(range(1, 13))
        index = [
            ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c", "c"],
            [1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2],
        ]
        y1 = pbtapply(x, index, sum)
        y2 = pbtapply(x, index, None)
        return [*y1.data, *y2]
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
