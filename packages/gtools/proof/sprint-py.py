import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.sprint import sprint


def one():
    try:
        sprint(1)
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
