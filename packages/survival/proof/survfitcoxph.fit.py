import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.survfitcoxph_fit import survfitcoxph_fit


def _read(name):
    csv_path = Path(__file__).with_name(name)
    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _col(rows, name):
    return np.array([float(row[name]) for row in rows], dtype=float)


def _load():
    train = _read("coxsurv.fit.train.csv")
    newd = _read("coxsurv.fit.newdata.csv")
    varrows = _read("coxsurv.fit.varmat.csv")
    varmat = np.array([[float(row[key]) for key in ("v1", "v2", "v3")] for row in varrows], dtype=float)
    return {
        "y": np.column_stack([_col(train, "time"), _col(train, "status")]),
        "x": np.column_stack([_col(train, "age"), _col(train, "sex"), _col(train, "ph_ecog")]),
        "wt": _col(train, "wt"),
        "risk": _col(train, "risk"),
        "strata": _col(train, "strata").astype(int),
        "varmat": varmat,
        "x2": np.column_stack([_col(newd, "age"), _col(newd, "sex"), _col(newd, "ph_ecog")]),
        "risk2": _col(newd, "risk2"),
        "strata2": _col(newd, "strata2").astype(int),
        "id2": _col(newd, "id2").astype(int),
        "y2": np.column_stack([_col(newd, "start"), _col(newd, "stop")]),
    }


_FIELDS = ["n", "time", "n.risk", "n.event", "n.censor", "strata", "surv", "cumhaz", "std.err"]


def _flat(res):
    out = []
    for key in _FIELDS:
        if key not in res or res[key] is None:
            continue
        value = res[key]
        if isinstance(value, dict):
            out.extend(float(v) for v in value.values())
        else:
            out.extend(np.ravel(np.asarray(value, dtype=float), order="F").tolist())
    return out


def one(inp):
    a = survfitcoxph_fit(
        inp["y"],
        inp["x"],
        inp["wt"],
        inp["x2"][:2, :],
        inp["risk"],
        inp["risk2"][:2],
        inp["strata"],
        True,
        2,
        1,
        inp["varmat"],
    )
    b = survfitcoxph_fit(
        inp["y"],
        inp["x"],
        inp["wt"],
        inp["x2"][0:1, :],
        inp["risk"],
        inp["risk2"][0:1],
        inp["strata"],
        True,
        3,
        1,
        inp["varmat"],
    )
    c = survfitcoxph_fit(
        inp["y"],
        inp["x"],
        inp["wt"],
        inp["x2"],
        inp["risk"],
        inp["risk2"],
        inp["strata"],
        True,
        2,
        3,
        inp["varmat"],
        inp["id2"],
        inp["y2"],
        inp["strata2"],
    )
    vals = _flat(a) + _flat(b) + _flat(c)
    return ["NA" if v != v else f"{v:.17g}" for v in vals]


if __name__ == "__main__":
    inp = _load()
    value = one(inp)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one(inp)
        elapsed.append((time.perf_counter() - started) * 1000)
    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")
