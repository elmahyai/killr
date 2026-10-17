import json
import statistics
import time

from pbapply.closepb import closepb
from pbapply.getpb import getpb
from pbapply.pboptions import pboptions
from pbapply.startpb import startpb


def numopts(o):
    return [
        float(o["style"]),
        float(o["txt.width"]),
        float(o["gui.width"]),
        float(o["initial"]),
        float(o["nout"]),
        float(o["min_time"]),
        float(o["use_lb"]),
    ]


def one():
    out = []
    opb = pboptions(type="txt", style=1, char=">", initial=0.5, nout=50)
    out.extend(numopts(opb))
    pb = startpb(0, 10)
    out.append(getpb(pb))
    closepb(pb)
    pboptions(style=3, initial=0.25)
    pb = startpb(0, 10)
    out.append(getpb(pb))
    closepb(pb)
    pboptions(opb)
    pb = startpb(0, 10)
    if pb is not None:
        out.append(getpb(pb))
    closepb(pb)
    out.extend(numopts(pboptions()))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
