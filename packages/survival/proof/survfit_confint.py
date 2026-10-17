import statistics
import time

import numpy as np
from survival.survfit_confint import survfit_confint


def fmt(values):
    return " ".join(f"{float(v):.17g}" for v in np.asarray(values, dtype=float).ravel())


def lines_for(label, res):
    return [f"{label} lower {fmt(res['lower'])}", f"{label} upper {fmt(res['upper'])}"]


def one():
    p = np.array([0.95, 0.8, 0.5, 0.2])
    se = np.array([0.02, 0.05, 0.1, 0.04])
    selow = np.array([0.01, 0.0, 0.08, 0.03])
    out = []
    for ct in ["plain", "log", "log-log", "logit", "arcsin"]:
        for lg in [True, False]:
            flag = "logse" if lg else "nologse"
            out.extend(lines_for(f"{ct} {flag} nosel",
                                 survfit_confint(p, se, logse=lg, conf_type=ct, conf_int=0.9)))
            out.extend(lines_for(f"{ct} {flag} selow",
                                 survfit_confint(p, se, logse=lg, conf_type=ct, conf_int=0.9,
                                                 selow=selow)))
    out.extend(lines_for("plain ulimit_false",
                         survfit_confint(p, se, conf_type="plain", ulimit=False)))
    out.extend(lines_for("log ulimit_false",
                         survfit_confint(p, se, conf_type="log", ulimit=False)))
    out.extend(lines_for("log-log p1",
                         survfit_confint(np.array([1.0, 0.6]), np.array([0.0, 0.1]),
                                         conf_type="log-log")))
    out.extend(lines_for("logit p1",
                         survfit_confint(np.array([1.0, 0.6]), np.array([0.0, 0.1]),
                                         conf_type="logit")))
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
