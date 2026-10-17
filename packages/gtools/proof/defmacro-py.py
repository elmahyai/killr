import json
import statistics
import sys
import time

_ROOT = "/home/ahmed/killr_projects/killr/packages"
for _pkg in ("evaluate", "rlang", "gtools"):
    sys.path.insert(0, f"{_ROOT}/{_pkg}")

from rlang.as_label import Call  # noqa: E402
from rlang.as_string import Symbol  # noqa: E402

from gtools.defmacro import defmacro  # noqa: E402


def one():
    mul = defmacro("a", "b", expr="a * b")
    i, j, k = 2, 3, 4
    return [
        float(mul(2, Call(Symbol("+"), 3, 4))),
        float(mul(Symbol("i"), Call(Symbol("+"), Symbol("j"), Symbol("k")))),
    ]


invisible = one()
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
