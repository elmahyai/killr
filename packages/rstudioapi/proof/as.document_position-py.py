import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rstudioapi.as_document_position import as_document_position, document_position


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
        if hasattr(value, "row") and hasattr(value, "column"):
            text = "OK " + _num(value.row) + " " + _num(value.column)
            if same is not None:
                text += " " + ("TRUE" if value is same else "FALSE")
        else:
            text = "OTHER " + repr(value)
    return name + "=" + text


def one():
    pos = document_position(3, 7)
    parts = [
        line("identity", lambda: as_document_position(pos), same=pos),
        line("dbl", lambda: as_document_position((3.0, 7.0))),
        line("int", lambda: as_document_position((1, 2))),
        line("na", lambda: as_document_position((float("nan"), 1.0))),
        line("len3", lambda: as_document_position((1.0, 2.0, 3.0))),
        line("logical", lambda: as_document_position((True, False))),
        line("char", lambda: as_document_position(("a", "b"))),
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
