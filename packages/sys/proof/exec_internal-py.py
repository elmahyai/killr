import statistics
import time
from r_sys import exec_internal

def one():
        out = exec_internal("printf", ["%s", "hello"])
        return str(out["status"]) + "|" + ",".join(str(b) for b in out["stdout"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

if isinstance(value, (list, tuple)):
    shown = "|".join("" if item is None else str(item) for item in value)
elif value is None:
    shown = "NULL"
else:
    shown = str(value)
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
