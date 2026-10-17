import statistics
import time
from vctrs import vec_recycle_common

def one():
    out = vec_recycle_common(1, [1, 2, 3])
    return ",".join(str(item) for piece in out for item in piece)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
