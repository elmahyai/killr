import statistics
import time
import warnings
from r_sys import eval_safe

def one():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                eval_safe(1)
            except RuntimeError as exc:
                message = " / ".join(str(item.message).replace("\n", " / ") for item in caught)
                return message + " || " + str(exc)
        return "missing"

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
