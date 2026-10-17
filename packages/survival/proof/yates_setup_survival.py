import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.coxph import coxph
from survival.yates_setup import yates_setup

_CSV = Path(__file__).with_name("lung.csv")
ETA = np.linspace(-1, 1, 5)


def _vfun(p):
    return 0.01 * p**2 + 0.001


def _load():
    with _CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    cols = ["time", "status", "age", "sex", "ph_ecog"]
    data = {}
    for name in cols:
        data[name] = np.array([float(r[name]) if r[name] != "" else np.nan for r in rows], dtype=float)
    keep = np.all(np.isfinite(np.column_stack([data[c] for c in cols])), axis=1)
    data = {name: values[keep] for name, values in data.items()}
    data["status"] = data["status"] - 1.0
    return data


def _fmt(x):
    return [f"{float(v):.17g}" for v in np.asarray(x, dtype=float).ravel(order="F")]


def one(fit):
    out = []
    for options in (None, {"rmean": 300}):
        s = yates_setup(fit, predict="survival", options=options)
        p = s["predict"](ETA, None)
        sm = s["summary"](p, _vfun(p))
        out += _fmt(p)
        for key in ["n", "time", "n.risk", "n.event", "n.censor", "cumhaz", "surv", "std.err", "lower", "upper", "conf.int"]:
            out += _fmt(sm[key])
    return out


if __name__ == "__main__":
    data = _load()
    fit = coxph("Surv(time, status) ~ age + sex + ph_ecog", data, x=True)
    value = one(fit)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one(fit)
        elapsed.append((time.perf_counter() - started) * 1000)
    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")
