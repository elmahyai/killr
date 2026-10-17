import statistics
import time
from lifecycle import deprecated, is_present

def one():
    def g(baz=deprecated()):
        return is_present(baz)
    return ("TRUE" if g() else "FALSE") + " " + ("TRUE" if g(1) else "FALSE")

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
