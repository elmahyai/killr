import statistics
import time
from lifecycle import expect_deprecated, deprecate_warn

def one():
    try:
        expect_deprecated(lambda: deprecate_warn("9.0.0", "qqq()"))
        return "pass"
    except Exception:
        return "fail"

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
