from polynom import polynomial, as_character

def one():
    return as_character(polynomial([1, 2, 1]))

import statistics
import time
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
else:
    shown = str(value)
print("VALUE " + shown.replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
