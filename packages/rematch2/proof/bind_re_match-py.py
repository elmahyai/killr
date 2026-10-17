import statistics
import time

from rematch2 import bind_re_match
from tibble import tibble
cars = tibble(rowname=["Mazda RX4", "Datsun 710"], mpg=[21.0, 22.8])
pattern = r"^(?<make>\w+) ?(?<model>.+)?$"
def one():
    return ",".join(f"{m}={d}" for m, d in zip(bind_re_match(cars, "rowname", pattern)["make"], bind_re_match(cars, "rowname", pattern)["model"]))

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
