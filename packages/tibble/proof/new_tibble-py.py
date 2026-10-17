import statistics
import time

from tibble import new_tibble
def one():
    frame = new_tibble([[1, 2, 3], [4, 5, 6]], names=["a", "b"])
    return "|".join([",".join(map(str, frame["a"])), ",".join(map(str, frame["b"]))])

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
