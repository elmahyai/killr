import statistics
import time
from survival import blogit

def one():
    link = blogit()
    mu = [0.01, 0.2, 0.5, 0.9, 0.99]
    return [link["name"], *[f"{value:.17g}" for value in link["linkfun"](mu)]]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
