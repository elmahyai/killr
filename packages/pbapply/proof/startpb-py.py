import json
import math
import statistics
import time

from pbapply.startpb import closepb, getpb, replace_pboptions, reset_pboptions, startpb

PAIRS = [(0, 1), (0, 10), (2, 5), (-10, 10)]


def one():
    out = []
    former = replace_pboptions(
        type="timer",
        style=3,
        char="+",
        **{"txt.width": 50},
        initial=0,
        min_time=0,
    )
    try:
        for min_val, max_val in PAIRS:
            pb = startpb(min_val, max_val)
            out.append(float("nan") if pb is None else getpb(pb))
            closepb(pb)
        replace_pboptions(initial=0.25)
        pb = startpb(0, 10)
        out.append(getpb(pb))
        closepb(pb)
        replace_pboptions(type="none")
        pb = startpb(0, 1)
        out.append(float("nan") if pb is None else getpb(pb))
        closepb(pb)
    finally:
        reset_pboptions(former)
    return out


def json_number(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return x


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": [json_number(v) for v in value],
            "median_ms": statistics.median(elapsed),
        }
    )
)
