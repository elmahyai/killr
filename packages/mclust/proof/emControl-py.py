import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.em_control import em_control


def one():
    x = em_control(eps=1e-8, tol=1e-4, itmax=float("inf"), equal_pro=True)
    values = []
    for key in ("eps", "tol", "itmax"):
        component = x[key]
        if isinstance(component, (list, tuple)):
            values.extend(float(item) for item in component)
        else:
            values.append(float(component))
    equal = x["equalPro"]
    if isinstance(equal, (list, tuple)):
        values.extend(1.0 if item else 0.0 for item in equal)
    else:
        values.append(1.0 if equal else 0.0)
    return values


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
