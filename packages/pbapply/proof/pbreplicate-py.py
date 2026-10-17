import json
import statistics
import time

from pbapply.pbreplicate import pbreplicate
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        out = pbreplicate(6, lambda: max([1, 2, 3]), simplify=True)
        return [float(v) for v in out]
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
