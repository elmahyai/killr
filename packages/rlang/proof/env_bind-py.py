import statistics
import time

from rlang import env
from rlang.env_bind import env_bind


def one():
    e = env(a=10, b=20)
    old = env_bind(e, a=1, b=2, c=30)
    return old["a"] + old["b"] + e["a"] + e["b"] + e["c"]


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
