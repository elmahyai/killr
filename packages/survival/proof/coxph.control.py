import statistics
import time
from survival import coxph_control

def one():
    ctl = coxph_control()
    return [
        f"{ctl['eps']:.17g}",
        f"{ctl['toler.chol']:.17g}",
        f"{ctl['iter.max']:.17g}",
        f"{ctl['toler.inf']:.17g}",
        f"{ctl['outer.max']:.17g}",
        "1" if ctl["timefix"] else "0",
        ctl["survcheckallow"],
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
