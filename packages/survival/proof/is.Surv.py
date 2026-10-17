import statistics
import time
from survival import Surv, is_Surv

def one():
    return ["1" if is_Surv(Surv(1, 1)) else "0", "1" if is_Surv(1) else "0"]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
