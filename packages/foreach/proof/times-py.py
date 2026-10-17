import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from foreach.core import ForeachError, do, times


def fmt(value):
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return "C(" + value + ")"
    if isinstance(value, (list, tuple)):
        return "V(" + ",".join(format(float(item), ".17g") for item in value) + ")"
    return "V(" + format(float(value), ".17g") + ")"


def run(fn):
    try:
        return fmt(fn())
    except ForeachError as exc:
        return "ERR:" + exc.message


def one():
    parts = [
        run(lambda: do(times(4), 2)),
        run(lambda: do(times(1), 4)),
        run(lambda: do(times(0), 4)),
        run(lambda: do(times(1.5), 4)),
        run(lambda: do(times(3), 7)),
        run(lambda: do(times(5), lambda: 1 + 2)),
        run(lambda: do(times([3]), 8)),
        run(lambda: times(True)),
        run(lambda: times([1, 2])),
        run(lambda: times(None)),
        run(lambda: times("a")),
        run(lambda: do(times(float("nan")), 1)),
    ]
    return "|".join(parts)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + value)
print(f"MS {statistics.median(elapsed):.17g}")
