import statistics
import time
from rlang import is_installed

def one():
    return ("TRUE" if is_installed("base") else "FALSE") + " " + ("TRUE" if is_installed("no-such-pkg-zz") else "FALSE")

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
