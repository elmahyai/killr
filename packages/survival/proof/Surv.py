import statistics
import time
from survival import Surv

def one():
    a = Surv([1, 2.5, 10, float("nan")], [1, 0, 1, 1]).character()
    b = Surv([0, 1], [5, 6.25], [1, 0], type="counting").character()
    d = Surv([1, 2], [1, 3], type="interval2").character()
    e = Surv([1, 2], [0, 1], type="left").character()
    return ["|".join(a), "|".join(b), "|".join(d), "|".join(e)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
