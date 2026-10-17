import json
import math
import statistics
import time

from pbapply.pbsapply import pbsapply
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        roots = pbsapply([1, 4, 9], math.sqrt)
        empty = pbsapply([], math.sqrt)
        return [float(v) for v in roots] + [float(len(empty))]
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
