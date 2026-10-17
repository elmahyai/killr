import statistics
import time
from survival import Surv, aeqSurv

def one():
    s = aeqSurv(Surv([1, 1 + 1e-10, 5], [1, 1, 0]))
    lines = [f"{value:.17g}" for value in s.columns[:, 0]]
    lines += [f"{value:.17g}" for value in s.columns[:, 1]]
    return lines

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
