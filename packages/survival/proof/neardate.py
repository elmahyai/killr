import statistics
import time
from datetime import date

from survival.neardate import neardate


def _date(year, month, day):
    return date(int(year), int(month), int(day))


def serialize(values):
    tokens = []
    for value in values:
        if value is None:
            tokens.append("NA")
        else:
            tokens.append(str(int(value)))
    return ",".join(tokens)


def one():
    data1_id = list(range(1, 11))
    data1_entry = [_date(2011, month, 5) for month in range(1, 11)]
    temp1 = [1, 4, 5, 1, 3, 6, 9, 2, 7, 8, 12, 4, 6, 7, 10, 12, 3]
    data2_id = [1, 1, 1, 2, 2, 4, 4, 5, 5, 5, 6, 8, 8, 9, 10, 10, 12]
    data2_lab = [_date(2011, month, 1) for month in temp1]
    indx1 = neardate(data1_id, data2_id, data1_entry, data2_lab)
    indx2 = neardate(data1_id, data2_id, data1_entry, data2_lab, best="prior")
    return [serialize(indx1), serialize(indx2)]


t0 = time.perf_counter()
value = one()
py_untimed = (time.perf_counter() - t0) * 1000

elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
py_median = statistics.median(elapsed)

print("\n".join(value))
print("PY_UNTIMED")
print(f"{py_untimed:.17g}")
print("PY_MEDIAN")
print(f"{py_median:.17g}")
