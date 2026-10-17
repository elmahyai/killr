import importlib.util
import json
import math
import statistics
import sys
import time

_SCAT_PATH = "/home/ahmed/killr_projects/killr/packages/gtools/gtools/scat.py"
_spec = importlib.util.spec_from_file_location("gtools_scat", _SCAT_PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
scat = _mod.scat
set_debug = _mod.set_debug
R_NA = _mod.R_NA


def one() -> list[str]:
    set_debug(None)
    out: list[str] = []
    out.append(scat("Not displayed"))
    set_debug(True)
    out.append(scat("This will be displayed immediately (even in R BATCH output \n"))
    out.append(scat("files), provided options()$DEBUG is TRUE."))
    out.append(scat("a", "b", "c"))
    out.append(scat(1, 2, 3))
    out.append(scat(True, False))
    out.append(scat(["x", "y"]))
    set_debug(False)
    out.append(scat("hidden"))
    set_debug(True)
    out.append(scat("line1\n", "line2"))
    out.append(scat("num ", math.pi, " end"))
    out.append(scat(1 / 7, 2 / 7, 3 / 7))
    out.append(scat("mix", ["p", "q"], 42))
    out.append(scat(float("nan"), float("inf"), float("-inf"), R_NA))
    out.append(scat(complex(1, 2)))
    set_debug(1)
    out.append(scat("numeric TRUE"))
    set_debug(0)
    out.append(scat("numeric FALSE"))
    return out


invisible = one()
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
