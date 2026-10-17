import statistics
import time
from collections.abc import Mapping

import numpy as np

from survival.survreg_distributions import survreg_distributions
from survival.survreg_dtest import survregDtest


def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, (bool, np.bool_)):
        return "TRUE" if v else "FALSE"
    if isinstance(v, str):
        return v
    if isinstance(v, Mapping):
        v = list(v.values())
    flat = np.asarray(v, dtype=float).reshape(-1)
    parts = []
    for z in flat:
        if np.isnan(z):
            parts.append("NA")
        else:
            parts.append(f"{float(z):.17g}")
    return ",".join(parts)


def one():
    out = []

    def add(label, value):
        out.append(f"{label}|{value}")

    add("names", ",".join(survreg_distributions.keys()))

    x_grid = np.array([-2.0, -0.5, 0.0, 0.7, 1.5])
    p_grid = np.array([0.1, 0.25, 0.5, 0.75, 0.9])
    xi = np.array([1.0, 2.0, 3.0, 5.0, 8.0])
    wi = np.array([1.0, 1.0, 2.0, 1.0, 1.0])
    yy = np.column_stack(
        (
            np.array([1.0, 2.0, 1.5, 1.0, 0.5]),
            np.array([1.0, 2.0, 1.5, 2.5, 1.5]),
            np.array([1.0, 0.0, 2.0, 3.0, 3.0]),
        )
    )
    tr = np.array([0.5, 2.0])
    itr = np.array([-0.5, 0.7])

    for k, d in survreg_distributions.items():
        is_t = k == "t"
        prm = 4.0 if is_t else None

        add(f"{k}.name", fmt(d.get("name")))
        add(f"{k}.dist", fmt(d.get("dist")))
        add(f"{k}.scale", fmt(d.get("scale")))
        add(f"{k}.parms", fmt(d.get("parms")))

        variance = d.get("variance")
        add(f"{k}.variance", "NULL" if variance is None else fmt(variance(4.0)))

        init = d.get("init")
        if init is None:
            add(f"{k}.init", "NULL")
        elif is_t:
            add(f"{k}.init", fmt(init(xi, wi, 4.0)))
        else:
            add(f"{k}.init", fmt(init(xi, wi)))

        deviance = d.get("deviance")
        if deviance is None:
            add(f"{k}.center", "NULL")
            add(f"{k}.loglik", "NULL")
        else:
            r = deviance(yy, 2.0, prm)
            add(f"{k}.center", fmt(r["center"]))
            add(f"{k}.loglik", fmt(r["loglik"]))

        density = d.get("density")
        add(f"{k}.density", "NULL" if density is None else fmt(density(x_grid, prm)))

        quantile = d.get("quantile")
        add(f"{k}.quantile", "NULL" if quantile is None else fmt(quantile(p_grid, prm)))

        trans = d.get("trans")
        add(f"{k}.trans", "NULL" if trans is None else fmt(trans(tr)))
        dtrans = d.get("dtrans")
        add(f"{k}.dtrans", "NULL" if dtrans is None else fmt(dtrans(tr)))
        itrans = d.get("itrans")
        add(f"{k}.itrans", "NULL" if itrans is None else fmt(itrans(itr)))

        add(f"{k}.survregDtest", "TRUE" if survregDtest(d) else "FALSE")
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
