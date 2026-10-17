from polynom import poly_orth, coef

def one():
    orth = poly_orth([1, 2, 3, 4, 5], 2)
    values = coef(orth[0]) + coef(orth[1])
    return ",".join(f"{v:.17g}" for v in values)

import statistics
import time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
else:
    shown = str(value)
print("VALUE " + shown.replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
