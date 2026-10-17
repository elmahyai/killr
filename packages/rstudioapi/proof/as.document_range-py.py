import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rstudioapi.as_document_range import as_document_range, document_range


def _num(value: float) -> str:
    if math.isnan(value):
        return "NA"
    return format(float(value), ".17g")


def line(name, fn, same=None):
    try:
        value = fn()
    except Exception as exc:
        text = "ERR " + str(exc)
    else:
        if hasattr(value, "start") and hasattr(value, "end"):
            s = value.start
            e = value.end
            text = (
                "OK "
                + _num(s.row)
                + " "
                + _num(s.column)
                + " "
                + _num(e.row)
                + " "
                + _num(e.column)
            )
            if same is not None:
                text += " " + ("TRUE" if value is same else "FALSE")
        else:
            text = "OTHER " + repr(value)
    return name + "=" + text


def one():
    rng = document_range((1.0, 2.0, 3.0, 4.0))
    parts = [
        line("identity", lambda: as_document_range(rng), same=rng),
        line("dbl4", lambda: as_document_range((1.0, 2.0, 3.0, 4.0))),
        line("int4", lambda: as_document_range((1, 2, 3, 4))),
        line("na4", lambda: as_document_range((float("nan"), 2.0, 3.0, 4.0))),
        line("vec2", lambda: as_document_range((1.0, 2.0))),
        line("len3", lambda: as_document_range((1.0, 2.0, 3.0))),
        line("logical", lambda: as_document_range((True, False, True, False))),
    ]
    return "\n".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value.replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
