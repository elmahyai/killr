import statistics
import time
from survival import survreg_control

def one():
    a = survreg_control()
    b = survreg_control(iter_max=12)
    return [
        f"{a['maxiter']:.17g}",
        f"{a['rel.tolerance']:.17g}",
        f"{a['toler.chol']:.17g}",
        f"{a['iter.max']:.17g}",
        f"{a['debug']:.17g}",
        f"{a['outer.max']:.17g}",
        f"{b['maxiter']:.17g}",
        f"{b['iter.max']:.17g}",
    ]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
