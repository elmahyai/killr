from pathlib import Path
import sys
import time
import numpy as np

sys.path.insert(0, "packages/logspline")
from logspline.core import (
    print_logspline, print_oldlogspline, qlogspline, qoldlogspline,
    rlogspline, roldlogspline, rpqlsd, summary_logspline,
    summary_oldlogspline, unstrip,
)

OUT = Path("packages/logspline/docs/output")
OUT.mkdir(parents=True, exist_ok=True)

FIT = {
    "coef.pol": np.array([-2.0, 0.1]),
    "coef.kts": np.array([0.01, -0.02]),
    "knots": np.array([-1.0, 1.0]),
    "bound": np.array([1.0, -2.0, 1.0, 2.0]),
    "samples": np.array([100]),
    "penalty": np.log(100),
    "logl": np.array([[3, 2, -100.0], [4, 2, -99.0]]),
}

OLD = {
    "coef": np.array([-2.0, 0.1, 0.01, -0.02]),
    "knots": np.array([-1.0, 1.0]),
    "bound": FIT["bound"],
    "sample": 100,
    "penalty": np.log(100),
    "logl": np.array([-100.0, -99.0]),
    "delete": True,
}


def run(name, fn, arg):
    value = fn(arg)
    t = []
    for _ in range(20):
        start = time.perf_counter()
        fn(arg)
        t.append((time.perf_counter() - start) * 1000)
    (OUT / f"{name}-py.txt").write_text(repr(value) + "\n")
    print(name, "translated_ms", float(np.median(t)))
    return value
