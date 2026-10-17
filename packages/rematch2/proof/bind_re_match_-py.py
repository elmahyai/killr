import statistics
import time

from rematch2 import bind_re_match_
from tibble import tibble
cars = tibble(rowname=["Mazda RX4", "Datsun 710"], mpg=[21.0, 22.8])
def one():
    return "|".join(bind_re_match_(cars, "rowname", r"^(?<make>\w+) ?(?<model>.+)?$", keep_match=True)[".match"])

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
