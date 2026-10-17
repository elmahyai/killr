import statistics
import time
import time
from r_sys import exec_background, exec_status

def one():
        pid = exec_background("false", std_out=False, std_err=False)
        time.sleep(0.05)
        return exec_status(pid, wait=True)

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
