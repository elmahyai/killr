import statistics
import time

import numpy as np
from survival.survfit0 import survfit0


def mat(values, nrow):
    """Column-major matrix, the same layout as R matrix(values, nrow=nrow)."""
    return np.array(values, dtype=float).reshape((nrow, -1), order="F")


def vec(values):
    return np.array(values, dtype=float)


def fit(cls, **fields):
    return {"class_": cls, **fields}


def case_a():
    return fit(
        ("survfit",),
        n=5,
        time=vec([1, 2, 4, 7]),
        **{"n.risk": vec([5, 4, 3, 1]), "n.event": vec([1, 0, 1, 1]), "n.censor": vec([0, 1, 1, 0])},
        surv=vec([0.8, 0.8, 0.4, 0.2]),
        **{"std.err": vec([0.1, 0.1, 0.2, 0.3])},
        upper=vec([0.95, 0.95, 0.7, 0.6]),
        lower=vec([0.6, 0.6, 0.2, 0.1]),
        **{"influence.surv": mat([0.1, -0.2, 0.3, 0.4, -0.5, 0.6, 0.7, -0.8], 2)},
        logse=True,
        **{"conf.int": 0.95, "conf.type": "log"},
        time0=False,
        type="right",
    )


def case_b():
    x = case_a()
    del x["influence.surv"]
    x["cumhaz"] = vec([0.2231, 0.2231, 0.9163, 1.6094])
    x["logse"] = False
    return x


def case_c():
    return fit(
        ("survfit",),
        n=vec([3, 2]),
        time=vec([1, 2, 4, 0, 3]),
        **{"n.risk": vec([5, 4, 2, 2, 1]), "n.event": vec([1, 0, 1, 0, 1]), "n.censor": vec([0, 1, 0, 1, 0])},
        surv=vec([0.8, 0.8, 0.4, 1, 0.5]),
        **{"std.err": vec([0.1, 0.1, 0.2, 0, 0.3])},
        cumhaz=vec([0.2231, 0.2231, 0.9163, 0, 0.6931]),
        strata=vec([3, 2]),
        logse=True,
        **{"conf.type": "log"},
        type="right",
    )


def case_d():
    return fit(
        ("survfit",),
        n=vec([2, 3]),
        time=vec([1, 2, 3, 5, 6]),
        **{"n.risk": vec([5, 4, 3, 2, 1]), "n.event": vec([1, 0, 1, 0, 1]), "n.censor": vec([0, 1, 0, 1, 0])},
        surv=vec([0.8, 0.8, 0.5, 0.5, 0.25]),
        **{"std.err": vec([0.1, 0.1, 0.2, 0.2, 0.3])},
        strata=vec([2, 3]),
        logse=True,
        **{"conf.type": "log"},
        type="right",
    )


def case_e():
    return fit(
        ("survfit",),
        n=6,
        time=vec([1, 2, 4, 7]),
        **{"n.risk": vec([6, 5, 3, 2]), "n.event": vec([1, 0, 1, 1]), "n.censor": vec([0, 1, 0, 0])},
        surv=mat([0.9, 0.9, 0.6, 0.5, 0.8, 0.7, 0.5, 0.4], 4),
        **{"std.err": mat([0.05, 0.05, 0.1, 0.12, 0.06, 0.07, 0.11, 0.13], 4)},
        cumhaz=mat([0.105, 0.105, 0.51, 0.69, 0.22, 0.36, 0.69, 0.92], 4),
        upper=mat([0.97, 0.97, 0.8, 0.7, 0.95, 0.9, 0.8, 0.7], 4),
        lower=mat([0.8, 0.8, 0.4, 0.3, 0.6, 0.5, 0.3, 0.2], 4),
        logse=True,
        type="right",
    )


def case_f():
    return fit(
        ("survfitms", "survfit"),
        n=vec([3, 2]),
        time=vec([1, 2, 4, 0, 3]),
        **{
            "n.risk": mat([4, 3, 1, 2, 1, 0, 1, 2, 0, 1], 5),
            "n.event": mat([1, 0, 1, 0, 0, 0, 1, 0, 1, 1], 5),
        },
        pstate=np.array(
            [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20,
             0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34, 0.36, 0.38, 0.40]
        ).reshape((5, 2, 2), order="F"),
        p0=mat([0.9, 0.8, 0.1, 0.2], 2),
        sp0=mat([0.01, 0.02, 0.03, 0.04], 2),
        cumhaz=mat([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], 5),
        **{"std.err": mat([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10], 5)},
        lower=mat([0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.4, 0.4, 0.5, 0.5], 5),
        upper=mat([0.9, 0.9, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.5, 0.5], 5),
        strata=vec([3, 2]),
        states=np.array(["cens", "event"]),
    )


def case_g():
    return fit(
        ("survfitms", "survfit"),
        n=4,
        time=vec([1, 2, 5]),
        **{
            "n.risk": mat([4, 3, 2, 3, 2, 1], 3),
            "n.event": mat([1, 0, 1, 0, 1, 0], 3),
        },
        pstate=np.array([0.7, 0.6, 0.5, 0.3, 0.4, 0.5]).reshape((3, 1, 2), order="F"),
        p0=mat([0.7, 0.3], 1),
        sp0=mat([0.02, 0.03], 1),
        cumhaz=mat([0.3, 0.4, 0.5, 0.6, 0.7, 0.8], 3),
        **{"std.err": mat([0.1, 0.2, 0.3, 0.1, 0.2, 0.3], 3)},
        lower=mat([0.2, 0.3, 0.4, 0.1, 0.2, 0.3], 3),
        upper=mat([0.8, 0.7, 0.6, 0.9, 0.8, 0.7], 3),
        states=np.array(["cens", "event"]),
    )


def case_h():
    return fit(
        ("survfit",),
        n=3,
        time=vec([0, 2, 3]),
        **{"n.risk": vec([3, 2, 1]), "n.event": vec([0, 1, 1]), "n.censor": vec([0, 0, 0])},
        surv=vec([1, 0.5, 0.25]),
        **{"std.err": vec([0, 0.2, 0.3])},
        cumhaz=vec([0, 0.6931, 1.3863]),
        logse=True,
        type="right",
    )


def case_i():
    return fit(
        ("survfit",),
        n=3,
        time=vec([1, 2]),
        **{"n.risk": vec([3, 2]), "n.event": vec([1, 1]), "n.censor": vec([0, 0])},
        surv=vec([0.66, 0.33]),
        time0=True,
        type="right",
    )


def case_j():
    x = case_a()
    x["class_"] = ("survfit0", "survfit")
    return x


def serialize_fit(label, obj):
    out = [label, "class " + "|".join(obj["class_"])]
    for key in sorted(obj):
        if key == "class_":
            continue
        value = obj[key]
        if value is None or isinstance(value, list):
            continue
        arr = np.asarray(value)
        if arr.dtype.kind in "USO":
            continue
        vals = np.asarray(arr, dtype=float).ravel(order="F")
        out.append(f"{key} " + " ".join(f"{v:.17g}" for v in vals))
    return out


def one():
    cases = {
        "A": case_a(), "B": case_b(), "C": case_c(), "D": case_d(), "E": case_e(),
        "F": case_f(), "G": case_g(), "H": case_h(), "I": case_i(), "J": case_j(),
    }
    out = []
    for name, obj in cases.items():
        res = survfit0(obj)
        out.extend(serialize_fit(f"case {name}", res))
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
