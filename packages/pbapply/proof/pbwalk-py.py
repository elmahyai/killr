import json
import statistics
import time

from pbapply.pbwalk import pbwalk
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    former = replace_pboptions(type="none")
    try:
        z = {"a": 1, "b": 2, "c": 3}
        acc = [0]

        def bump(x):
            acc[0] += x

        pbwalk(z, bump)
        ret = pbwalk([10, 20], sum)
        return [float(acc[0]), float(ret[0]), float(ret[1])]
    finally:
        reset_pboptions(former)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
