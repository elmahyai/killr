import statistics
import time
from datetime import date, datetime
from assertthat import is_date
from assertthat.objects import NA

def one():
    return [is_date(datetime.now()), is_date(date.today()), is_date(1), is_date(NA), is_date(None)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(" ".join("1" if item else "0" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
