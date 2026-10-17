import statistics
import time

import numpy as np

from survival.fromtimeline import Categorical
from survival.surv import Surv
from survival.survexp import survexp


def make_rt():
    return {
        "class_": "ratetable",
        "data": np.arange(1, 7, dtype=float),
        "dim": [2, 3],
        "dimnames": [["a", "b"], ["x", "y", "z"]],
        "dimnames_names": ["dim1", "dim2"],
        "type": [2, 1],
        "cutpoints": [[0.0, 1.0], None],
    }


def serialize(fit):
    return [
        ",".join(f"{v:.17g}" for v in np.asarray(fit["time"]).reshape(-1)),
        ",".join(f"{v:.17g}" for v in np.asarray(fit["surv"]).reshape(-1)),
        ",".join(f"{v:.17g}" for v in np.asarray(fit["n.risk"]).reshape(-1)),
        str(fit["method"]),
    ]


def one():
    df = {
        "time": np.array([0.5, 1.5, 0.25, 2.0]),
        "dim1": np.array([0.25, 0.75, 1.25, 0.5]),
        "dim2": Categorical(["x", "y", "z", "x"], ["x", "y", "z"]),
    }
    fit = survexp(
        "Surv(time) ~ 1",
        data=df,
        ratetable=make_rt(),
        rmap={"dim1": "dim1", "dim2": "dim2"},
        method="ederer",
    )
    return serialize(fit)


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
