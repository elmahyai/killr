import statistics
import time
from curl import new_handle, handle_setheaders

def one():
    try:
        handle_setheaders(new_handle(), A=1)
    except RuntimeError as exc:
        return str(exc)
    return "ok"

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
