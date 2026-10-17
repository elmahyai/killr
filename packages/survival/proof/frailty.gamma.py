import statistics
import time

import numpy as np

from survival.frailty_gamma import _frailty_gammacon, frailty_gamma


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


def one():
    group = ["a", "a", "b", None, "c", "a", "b", "c", "a"]
    status = [1, 0, 1, 0, 1, 0, 1, 0, 1]
    x = frailty_gamma(group, theta=1, method="fixed")
    coef = [0.2, -0.1, 0.05]
    r0 = x.pfun(coef, 1, 3)
    r0z = x.pfun(coef, 0, 3)
    out = []
    for item in x.data.ravel():
        if item is None or (isinstance(item, float) and np.isnan(item)):
            out.append("NA")
        elif isinstance(item, str):
            out.append(item)
        else:
            out.append(_fmt(item))
    out.append(_fmt(x.sparse))
    out.extend(x.varname)
    out.append(_fmt(x.cparm["theta"]))
    out.extend(
        [
            _fmt(r0["recenter"]),
            _fmt(r0["penalty"]),
            *_fmt(r0["first"]),
            *_fmt(r0["second"]),
            _fmt(r0["flag"]),
            _fmt(r0z["penalty"]),
            _fmt(r0z["flag"]),
        ]
    )
    hist = {"theta": 1, "c.loglik": -12.345}
    pr = x.printfun(coef, [0.5, 0.4, 0.3], None, 3, hist)
    out.extend(_fmt(pr["coef"]))
    out.append(pr["history"])

    x2 = frailty_gamma(group, method="em", eps=1e-4)
    c0 = x2.cfun(x2.cparm, 0, {}, group, status, -10.5)
    c1 = x2.cfun(x2.cparm, 1, c0, group, status, -10.2)
    out.extend([_fmt(c0["theta"]), _fmt(c1["theta"]), _fmt(c1["c.loglik"])])

    d = np.array([2, 1, 3, 1], dtype=float)
    out.append(_fmt(_frailty_gammacon(d, 0.5)))

    x3 = frailty_gamma(group, df=2, method="df", eps=0.1)
    cp3 = x3.cparm
    out.extend([_fmt(cp3["df"]), _fmt(cp3["guess"]), _fmt(cp3["eps"])])

    big = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    x4 = frailty_gamma(big, method="fixed", theta=0.5)
    for item in x4.data.ravel():
        out.append(_fmt(item))
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
