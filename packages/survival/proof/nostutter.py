import statistics
import time

from survival.fromtimeline import Categorical
from survival.nostutter import nostutter


def _serialize_factor(cat: Categorical) -> str:
    tokens = []
    for value in cat.values:
        if value is None:
            tokens.append("NA")
        else:
            tokens.append(str(value))
    return ",".join(tokens)


def one():
    id_ = [1, 1, 1, 1, 2, 2, 2, 3, 3]
    ev = Categorical(
        ["censor", "a", "a", "b", "a", "b", "b", "censor", "b"],
        ["censor", "a", "b"],
    )
    y1 = nostutter(id_, ev, censor="censor")
    xnum = [0, 1, 1, 2, 1, 2, 2, 0, 2]
    y2 = nostutter(id_, xnum, censor=0)
    id2 = [1, 1, 1, 2, 2]
    ev2 = Categorical(["a", None, "a", "a", "b"], ["censor", "a", "b"])
    y3 = nostutter(id2, ev2, censor="censor")
    return [
        _serialize_factor(y1),
        _serialize_factor(y2),
        _serialize_factor(y3),
        "|".join(y1.levels),
        "|".join(y2.levels),
        "|".join(y3.levels),
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
