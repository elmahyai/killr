import statistics
import time
from survival import Surv, format_Surv

def one():
    s = Surv([1, 2.5, 10, float("nan")], [1, 0, 1, 1])
    return ["[" + item + "]" for item in format_Surv(s)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
