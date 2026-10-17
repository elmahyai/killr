import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.coxsurv_fit import coxsurv_fit


def _read(name):
    csv_path = Path(__file__).with_name(name)
    if not csv_path.is_file():
        raise FileNotFoundError(f"proof/{name} missing")
    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _col(rows, name):
    return np.array([float(r[name]) for r in rows], dtype=float)


def _load():
    train = _read("coxsurv.fit.train.csv")
    newd = _read("coxsurv.fit.newdata.csv")
    varrows = _read("coxsurv.fit.varmat.csv")
    # varmat.csv has a header row with v1,v2,v3 and then three rows of values
    varmat = np.array([[float(r[k]) for k in ("v1", "v2", "v3")] for r in varrows], dtype=float)
    y = np.column_stack([_col(train, "time"), _col(train, "status")])
    x = np.column_stack([_col(train, "age"), _col(train, "sex"), _col(train, "ph_ecog")])
    return {
        "y": y,
        "x": x,
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
    a = coxsurv_fit(
        1,
        2,
        True,
        inp["varmat"],
        False,
        inp["y"],
        inp["x"],
        inp["wt"],
        inp["risk"],
        None,
        inp["strata"],
        None,
        None,
        inp["x2"][:2, :],
        inp["risk2"][:2],
    )
    b = coxsurv_fit(
        2,
        2,
        True,
        inp["varmat"],
        False,
        inp["y"],
        inp["x"],
        inp["wt"],
        inp["risk"],
        None,
        inp["strata"],
        None,
        None,
        inp["x2"][0:1, :],
        inp["risk2"][0:1],
    )
    c = coxsurv_fit(
        1,
        2,
        True,
        inp["varmat"],
        False,
        inp["y"],
        inp["x"],
        inp["wt"],
        inp["risk"],
        None,
        inp["strata"],
        None,
        inp["y2"],
        inp["x2"],
        inp["risk2"],
        inp["strata2"],
        inp["id2"],
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
