import statistics
import time
from assertthat import TryError, is_error
from assertthat.objects import NA

def one():
    return [is_error(TryError('!!')), is_error(1), is_error(NA), is_error(None)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
