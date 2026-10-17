import statistics
import time
from lifecycle import deprecate_stop

def one():
    from lifecycle import LifecycleError
    try:
        deprecate_stop("1.0.0", "foo()", "bar()")
    except LifecycleError as exc:
        return str(exc).replace("\n", " / ")

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
