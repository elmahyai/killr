import statistics
import time

from survival.lvcf import lvcf
from survival.strata import StrataFactor


def _serialize(parts):
    lines = []
    for item in parts:
        if isinstance(item, StrataFactor):
            level_map = {code: level for code, level in enumerate(item.levels, start=1)}
            tokens = []
            for code in item.codes:
                if code is None:
                    tokens.append("NA")
                else:
                    tokens.append(level_map[code])
            lines.append(",".join(tokens))
        elif isinstance(item, list) and item and isinstance(item[0], bool):
            tokens = []
            for value in item:
                if value is None:
                    tokens.append("NA")
                elif value:
                    tokens.append("TRUE")
                else:
                    tokens.append("FALSE")
            lines.append(",".join(tokens))
        else:
            tokens = []
            for value in item:
                if value is None or (isinstance(value, float) and value != value):
                    tokens.append("NA")
                elif isinstance(value, float):
                    tokens.append(f"{value:.17g}")
                else:
                    tokens.append(str(value))
            lines.append(",".join(tokens))
    return lines


def one():
    id_ = [2, 1, 1, 2, 1, 2, 1, 1]
    time = [3, 2, 1, 1, 4, 2, 3, 5]
    platelet = [200, None, 150, None, None, 180, 160, None]
    diabetes = [None, 0, 1, None, None, 0, 1, 1]
    active = [None, True, False, None, None, True, None, False]
    stage = StrataFactor([2, None, 1, 2, None, 1, None, 2], ["A", "B", "C"])

    a = lvcf(id_, platelet, time)
    b = lvcf(id_, diabetes, time, first=True)
    c = lvcf(id_, active, time, first=True)
    d = lvcf(id_, stage, time)
    e = lvcf([3, 1, 2, 1, 3], [10, None, None, 20, None])
    return _serialize([a, b, c, d, e])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
