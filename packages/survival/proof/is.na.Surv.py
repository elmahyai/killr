import statistics
import time
from survival import Surv, is_na_Surv

def one():
    flags = is_na_Surv(Surv([1, float("nan"), 3], [1, 1, 0]))
    return ["1" if flag else "0" for flag in flags]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
