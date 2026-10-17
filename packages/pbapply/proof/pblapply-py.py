import json
import statistics
import time

from pbapply.pblapply import pblapply
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none", nout=3)
    try:
        x = list(range(1, 11))
        out = [float(v) for v in pblapply(x, lambda i: i * i)]
        out.append(float(len(pblapply([], lambda i: i))))
        return out
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
