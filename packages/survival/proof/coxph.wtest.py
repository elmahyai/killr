import statistics
import time
from survival import coxph_wtest

def one():
    w = coxph_wtest([[2.0, 0.5], [0.5, 1.0]], [1.0, -1.0])
    w1 = coxph_wtest(2, 3)
    solve = float(w1["solve"]) if not hasattr(w1["solve"], "__len__") else float(w1["solve"].reshape(-1)[0])
    return [
        f"{w['test']:.17g}",
        f"{w['df']}",
        *[f"{value:.17g}" for value in w["solve"]],
        f"{w1['test']:.17g}",
        f"{w1['df']}",
        f"{solve:.17g}",
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
