import statistics
import time

from lifecycle import LifecycleError, lifecycle_linter


def one():
    try:
        lifecycle_linter()
    except LifecycleError as exc:
        return str(exc)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
