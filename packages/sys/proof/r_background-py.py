import statistics
import time
from r_sys import exec_status, r_background

def one():
        pid = r_background(["--vanilla", "-q", "--slave", "-e", "quit(status=0)"], std_out=False, std_err=False)
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
