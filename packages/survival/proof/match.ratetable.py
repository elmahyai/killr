import statistics
import time

import numpy as np

from survival.fromtimeline import Categorical
from survival.match_ratetable import match_ratetable


def make_rt():
    return {
        "class": "ratetable",
        "data": np.arange(1, 7, dtype=float),
        "dim": [2, 3],
        "dimnames": [["a", "b"], ["x", "y", "z"]],
        "dimnames_names": ["dim1", "dim2"],
        "type": [2, 1],
        "cutpoints": [[0.0, 1.0], None],
    }


def serialize_match(fit):
    rflat = fit["R"].reshape(-1, order="F")
    tokens = [f"{v:.17g}" for v in rflat]
    cp = fit["cutpoints"]
    cp1 = "NULL" if cp[0] is None else ",".join(f"{v:.17g}" for v in np.asarray(cp[0]).reshape(-1))
    cp2 = "NULL" if cp[1] is None else ",".join(f"{v:.17g}" for v in np.asarray(cp[1]).reshape(-1))
    return [",".join(tokens), cp1, cp2]


def one():
    rt = make_rt()
    rdata = {
        "dim1": np.array([0.25, 0.75, 1.25, 1.75], dtype=float),
        "dim2": Categorical(["x", "y", "z", "x"], ["x", "y", "z"]),
    }
    fit = match_ratetable(rdata, rt)
    return serialize_match(fit)


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
