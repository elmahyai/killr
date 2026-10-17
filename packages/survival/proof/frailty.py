import statistics
import time

import numpy as np

from survival.frailty import frailty


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
    return [_fmt(item) for item in arr]


def _append_vector(out, data):
    for item in np.asarray(data, dtype=object).ravel():
        if item is None or (isinstance(item, float) and np.isnan(item)):
            out.append("NA")
        elif isinstance(item, str):
            out.append(item)
        else:
            out.append(_fmt(item))


def one():
    group = ["a", "a", "b", None, "c", "a", "b", "c", "a"]
    status = [1, 0, 1, 0, 1, 0, 1, 0, 1]
    coef = [0.2, -0.1, 0.05]
    out = []

    xg = frailty(group, theta=1, method="fixed")
    r0 = xg.pfun(coef, 1, 3)
    _append_vector(out, xg.data)
    out.extend(
        [
            _fmt(xg.sparse),
            _fmt(xg.cparm["theta"]),
            _fmt(r0["penalty"]),
            *_fmt(r0["first"]),
            *_fmt(r0["second"]),
        ]
    )

    xg2 = frailty(group, distribution="gam", theta=1, method="fixed")
    _append_vector(out, xg2.data)
    out.append(_fmt(xg.pfun(coef, 1, 3)["penalty"]))

    xgu = frailty(group, distribution="gaussian", theta=1, method="fixed")
    rg = xgu.pfun(coef, 1, 3)
    _append_vector(out, xgu.data)
    out.extend(
        [
            _fmt(xgu.cparm["theta"]),
            _fmt(rg["penalty"]),
            *_fmt(rg["first"]),
            *_fmt(rg["second"]),
        ]
    )

    xt = frailty(group, distribution="t", theta=1, method="fixed", tdf=5)
    rt = xt.pfun(coef, 1, 3)
    _append_vector(out, xt.data)
    out.extend(
        [
            _fmt(xt.pparm),
            _fmt(xt.cparm["theta"]),
            _fmt(rt["penalty"]),
            *_fmt(rt["first"]),
            *_fmt(rt["second"]),
        ]
    )

    xem = frailty(group, method="em", eps=1e-4)
    c0 = xem.cfun(xem.cparm, 0, {}, group, status, -10.5)
    c1 = xem.cfun(xem.cparm, 1, c0, group, status, -10.2)
    out.extend([_fmt(c0["theta"]), _fmt(c1["theta"]), _fmt(c1["c.loglik"])])

    big = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    x4 = frailty(big, distribution="gamma", method="fixed", theta=0.5)
    _append_vector(out, x4.data)
    out.append(_fmt(x4.sparse))
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
