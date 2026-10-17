import statistics
import time

from xts import firstof

def one():
    return format(firstof(2000), ".17g")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("TRUE" if value is True else "FALSE" if value is False else value)
print("%.17g" % statistics.median(elapsed))
