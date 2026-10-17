import io
import json
import math
import statistics
import time

from pbapply.closepb import closepb
from pbapply.getpb import getpb
from pbapply.setpb import setpb
from pbapply.startpb import replace_pboptions, reset_pboptions
from pbapply.timerProgressBar import timerProgressBar


def quiet_run(**kwargs):
    sink = io.StringIO()
    former = replace_pboptions(type="timer")
    try:
        pb = timerProgressBar(**kwargs, file=sink)
        out = [getpb(pb)]
        out.append(setpb(pb, 2.5))
        out.append(getpb(pb))
        out.append(setpb(pb, float("nan")))
        out.append(getpb(pb))
        out.append(setpb(pb, 100))
        out.append(getpb(pb))
        out.append(setpb(pb, 5))
        out.append(getpb(pb))
        closepb(pb)
        return out
    finally:
        reset_pboptions(former)


def one():
    out = []
    for sty in range(1, 7):
        out.extend(
            quiet_run(min=0, max=10, initial=0, style=sty, width=35, char="+")
        )
    out.extend(
        quiet_run(min=0, max=10, initial=0.25, style=3, width=50, char=".")
    )
    out.extend(
        quiet_run(min=2, max=5, initial=2, style=1, width=0, char="    ")
    )
    out.extend(
        quiet_run(min=-10, max=10, initial=-10, style=5, width=35, char="[=-]")
    )
    out.extend(quiet_run(min=0, max=1, initial=0, style=6, width=50, char="{*.}"))
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
