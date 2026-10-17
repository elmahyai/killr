import statistics
import time

import numpy as np

from survival.ridge import ridge


def _fmt(x):
    if isinstance(x, (bool, np.bool_)):
        return "TRUE" if x else "FALSE"
    if isinstance(x, str):
        return x
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    arr = np.asarray(x, dtype=float).ravel()
    if arr.size == 1:
        if np.isnan(arr[0]):
            return "NA"
        return f"{arr[0]:.17g}"
    return [ _fmt(item) for item in arr ]


def one():
    age = [50.0, 60.0, 55.0, float("nan"), 70.0]
    ecog = [0.0, 1.0, 0.0, 1.0, 2.0]
    x = ridge(age, ecog, theta=1)
    coef = [0.1, -0.2]
    r1 = x.pfun(coef, 1, 3, x.pparm)
    out = []
    out.extend(_fmt(x.data.ravel(order="C")))
    out.extend(_fmt(x.pparm))
    out.extend(x.varname)
    out.append(_fmt(x.cparm["theta"]))
    out.append(_fmt(r1["penalty"]))
    out.extend(_fmt(r1["first"]))
    out.extend(_fmt(r1["second"]))
    out.append(_fmt(r1["flag"]))
    x2 = ridge(age, ecog, df=1, eps=0.1)
    cp2 = x2.cparm
    out.extend(
        [
            _fmt(cp2["df"]),
            _fmt(cp2["eps"]),
            _fmt(cp2["thetas"]),
            _fmt(cp2["dfs"]),
            _fmt(cp2["guess"]),
        ]
    )
    x3 = ridge(age, ecog, theta=2, scale=False)
    r3 = x3.pfun(coef, 2, 3, x3.pparm)
    out.extend([_fmt(r3["penalty"]), *_fmt(r3["first"]), *_fmt(r3["second"])])
    cf = x.cfun(x.cparm, 1, {})
    out.extend([_fmt(cf["theta"]), _fmt(cf["done"])])
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
