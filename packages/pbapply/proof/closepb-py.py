import json
import math
import statistics
import time

from pbapply.closepb import closepb
from pbapply.startpb import (
    _TimerProgressBar,
    _TxtProgressBar,
    replace_pboptions,
    reset_pboptions,
    startpb,
)
from pbapply.setpb import setpb
from pbapply.getpb import getpb


def closed_flag(pb) -> float:
    if pb is None:
        return float("nan")
    if isinstance(pb, (_TxtProgressBar, _TimerProgressBar)):
        return 0.0 if pb._closed else 1.0
    return float("nan")


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
        for min_val, max_val in [(0, 10), (2, 5)]:
            pb = startpb(min_val, max_val)
            setpb(pb, min_val + 3)
            out.append(getpb(pb))
            closepb(pb)
            out.append(closed_flag(pb))
        closepb(None)
        out.append(0.0)
        replace_pboptions(type="none")
        closepb(startpb(0, 1))
        out.append(0.0)
        replace_pboptions(type="txt")
        pb = startpb(0, 5)
        setpb(pb, 2)
        out.append(getpb(pb))
        closepb(pb)
        out.append(closed_flag(pb))
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
