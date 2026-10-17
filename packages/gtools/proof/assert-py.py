import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
import gtools.defunct as gtools_defunct


def one():
    try:
        getattr(gtools_defunct, "assert")(True)
        return "\n"
    except RuntimeError as exc:
        return str(exc) + "\n"


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
