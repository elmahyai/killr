import statistics
import time

from survival.strata import StrataFactor, _as_factor, levels, strata


def _factor(values, labels=None):
    if labels is not None:
        codes = []
        for item in values:
            if item is None or (isinstance(item, float) and item != item):
                codes.append(None)
            else:
                codes.append(int(item))
        return StrataFactor(codes, list(labels))
    return _as_factor(values)


def serialize(x):
    codes = []
    for code in x.codes:
        if code is None:
            codes.append("NA")
        else:
            codes.append(str(int(code)))
    return ["|".join(levels(x)), "|".join(codes)]


def one():
    a = _factor([1, 2, 3] * 4, labels=["low", "medium", "high"])
    b = _factor([1, 2, 3, 4] * 3)
    c = [1, 2, None, 3, 1]
    d = _factor(["x", "y", "x", None, "y"])
    s1 = strata(b)
    s2 = strata(a, b, shortlabel=True)
    s3 = strata(a, b, na_group=True, sep=" | ")
    s4 = strata(c, d, shortlabel=True)
    out = []
    for item in (s1, s2, s3, s4):
        out.extend(serialize(item))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
