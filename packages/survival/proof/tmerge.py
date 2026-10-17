import math
import statistics
import time

from survival.tmerge import cumevent, cumtdc, event, tdc, tmerge


def _serialize_num(x):
    parts = []
    for v in x:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            parts.append("NA")
        else:
            parts.append(f"{float(v):.17g}" if isinstance(v, (int, float)) else str(v))
    return "|".join(parts)


def one():
    data1 = {"idd": [1, 5, 4, 3, 2, 6], "x1": list(range(1, 7)), "age": list(range(50, 56))}
    data2 = {"idd": [2, 5, 1, 2, 1], "x2": list(range(5, 0, -1)), "age": list(range(48, 43, -1))}
    test1 = tmerge(data1, data1, id="idd", death=event(data1["age"]))
    test2 = tmerge(test1, data2, id="idd", zed=tdc(data2["age"], data2["x2"]))
    data3 = {
        "idd": [5, 5, 1, 1, 6, 4, 3, 2],
        "age": [45, 50, 44, 48, 53, -5, 0, 20],
        "x": [1, 5, 2, 3, 7, 4, 6, 8],
    }
    test3 = tmerge(test2, data3, id="idd", x=cumtdc(data3["age"], data3["x"]), esum=cumevent(data3["age"]))
    tc = [int(v) for row in test3.tcount for v in row]
    cols = {n: c for n, c in zip(test3.names, test3.columns)}
    return [
        _serialize_num(cols["idd"]),
        _serialize_num(cols["tstop"]),
        _serialize_num(cols["death"]),
        _serialize_num(cols["zed"]),
        _serialize_num(cols["x"]),
        _serialize_num(cols["esum"]),
        "|".join(str(int(v)) for v in tc),
    ]


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
