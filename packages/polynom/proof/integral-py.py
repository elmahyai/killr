from polynom import polynomial, integral, as_character

def one():
    p = polynomial([1, 2, 1])
    return as_character(integral(p)) + " " + f"{integral(p, [0, 1])[0]:.17g}"

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
