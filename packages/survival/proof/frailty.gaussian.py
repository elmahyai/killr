import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/survival")
from survival.frailty_gaussian import frailty_gaussian


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
    x = frailty_gaussian(group, theta=1, method="fixed")
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
    hist = {"theta": 1}
    pr = x.printfun(coef, [0.5, 0.4, 0.3], None, 3, hist)
    out.extend(_fmt(pr["coef"]))
    out.append(pr["history"])

    x2 = frailty_gaussian(group, method="reml", eps=1e-4)
    c0 = x2.cfun(x2.cparm, 0, {})
    c1 = x2.cfun(x2.cparm, 1, c0, fcoef=coef, trH=0.5, loglik=-10.2)
    out.extend([_fmt(c0["theta"]), _fmt(c1["theta"]), _fmt(c1["history"][0, 1])])

    x3 = frailty_gaussian(group, df=2, method="df", eps=0.1)
    cp3 = x3.cparm
    out.extend([_fmt(cp3["df"]), _fmt(cp3["guess"]), _fmt(cp3["eps"])])

    x4 = frailty_gaussian(group, df=0)
    out.extend(list(x4.cargs))

    big = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    x5 = frailty_gaussian(big, method="fixed", theta=0.5)
    for item in x5.data.ravel():
        out.append(_fmt(item))
    out.append(_fmt(x5.sparse))
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
