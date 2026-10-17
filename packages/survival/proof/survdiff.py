import statistics
import time

import numpy as np

from survival.survdiff import survdiff

AML_TIME = [9, 13, 13, 18, 23, 28, 31, 34, 45, 48, 161, 5, 5, 8, 8, 12, 16, 23, 27, 30, 33, 43, 45]
AML_STATUS = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1]
AML_X = ["Maintained"] * 11 + ["Nonmaintained"] * 12

aml = {"time": [float(v) for v in AML_TIME], "status": [float(v) for v in AML_STATUS], "x": list(AML_X)}

aml_na = {"time": list(aml["time"]), "status": list(aml["status"]), "x": list(AML_X)}
aml_na["x"][6] = None

aml_near = {
    "time": [float(t) + (1e-12 if i % 2 == 0 else 0.0) for i, t in enumerate(AML_TIME, start=1)],
    "status": list(aml["status"]),
    "x": list(AML_X),
}

aml_off = {
    "time": list(aml["time"]),
    "status": list(aml["status"]),
    "x": list(AML_X),
    "p": [i / 24 for i in range(1, 24)],
}

N_SYN = 60
synth = {
    "time": [float(((i * 7) % 17) + 1) for i in range(1, N_SYN + 1)],
    "status": [int(i % 4 != 0) for i in range(1, N_SYN + 1)],
    "grp": [["B", "A", "C"][i % 3] for i in range(1, N_SYN + 1)],
    "s": [float(i % 2 + 1) for i in range(1, N_SYN + 1)],
    "z": [["u", "v", "w"][(i % 5) % 3] for i in range(1, N_SYN + 1)],
}


def vals(fit):
    out = []
    out.extend(np.asarray(fit["n"], dtype=float).ravel(order="F").tolist())
    out.extend(np.asarray(fit["obs"], dtype=float).ravel(order="F").tolist())
    out.extend(np.asarray(fit["exp"], dtype=float).ravel(order="F").tolist())
    out.extend(np.asarray(fit["var"], dtype=float).ravel(order="F").tolist())
    out.append(float(fit["chisq"]))
    out.append(float(fit["pvalue"]))
    if "strata" in fit:
        out.extend(np.asarray(fit["strata"], dtype=float).ravel(order="F").tolist())
    return out


def one():
    out = []
    out += vals(survdiff("Surv(time, status) ~ x", aml))
    out += vals(survdiff("Surv(time, status) ~ x", aml, rho=1))
    out += vals(survdiff("Surv(time, status) ~ x", aml, rho=0.5))
    out += vals(survdiff("Surv(time, status) ~ x", aml_na))
    out += vals(survdiff("Surv(time, status) ~ x", aml_near))
    out += vals(survdiff("Surv(time, status) ~ grp + strata(s)", synth))
    out += vals(survdiff("Surv(time, status) ~ grp + strata(s, z)", synth, rho=1))
    out += vals(survdiff("Surv(time, status) ~ grp", synth, rho=-1))
    out += vals(survdiff("Surv(time, status) ~ offset(p)", aml_off))
    out += vals(survdiff("Surv(time, status) ~ offset(p)", aml_off, rho=0.5))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(f"{item:.17g}" for item in value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
