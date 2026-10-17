import statistics
import time
from lifecycle import deprecate_warn, last_lifecycle_warnings

def one():
    def f():
        deprecate_warn("8.0.0", "abc()")
    f()
    return str(len(last_lifecycle_warnings()))

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
