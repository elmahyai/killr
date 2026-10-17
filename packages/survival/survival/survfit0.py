"""Insert a time-zero row into a survfit object (survival::survfit0).

A survfit object is a dict with the R element names. ``class_`` holds the
S3 class vector as a tuple. Matrices are NumPy 2-D arrays with time in rows,
and multi-state arrays are 3-D (time, curve, state), as in R.
"""

from __future__ import annotations

import numpy as np


def _classes(obj):
    classes = obj.get("class_", ())
    if isinstance(classes, str):
        return (classes,)
    return tuple(classes)


def _inherits(obj, name):
    return name in _classes(obj)


def _addto(x, insert, z):
    """R addto(): put z in front of the rows at 0-based positions ``insert``."""
    x = np.asarray(x)
    insert = np.asarray(insert, dtype=int)
    n_add = insert.size
    i2 = insert + np.arange(n_add)  # where the new rows land in the result
    n_new = x.shape[0] + n_add
    indx = np.setdiff1d(np.arange(n_new), i2)  # rows that keep old values

    if x.ndim == 3:
        dd1, dd2, dd3 = x.shape
        flat = x.reshape((dd1, dd2 * dd3), order="F")
        newx = np.empty((n_new, dd2 * dd3), dtype=float)
        newx[indx, :] = flat
        # rep(z, each = dd2), filled column-major into the new rows
        zz = np.repeat(np.asarray(z, dtype=float).ravel(order="F"), dd2)
        newx[i2, :] = zz.reshape((n_add, dd2 * dd3), order="F")
        return newx.reshape((n_new, dd2, dd3), order="F")

    if x.ndim == 2:
        newx = np.empty((n_new, x.shape[1]), dtype=float)
        newx[indx, :] = x
        newx[i2, :] = z
        return newx

    newx = np.empty(n_new, dtype=float)
    newx[indx] = x
    newx[i2] = z
    return newx


def _addcol(x):
    """R cbind(0, x)."""
    x2 = np.asarray(x, dtype=float)
    if x2.ndim == 1:
        x2 = x2.reshape(-1, 1)
    return np.hstack([np.zeros((x2.shape[0], 1)), x2])


def _addi0(arr, i0=0.0):
    """Influence array (obs, time, state): add a time-zero slice."""
    arr = np.asarray(arr, dtype=float)
    d0, d1, d2 = arr.shape
    temp = np.zeros((d0, 1 + d1, d2))
    temp[:, 1:, :] = arr
    if i0 is not None:
        temp[:, 0, :] = i0
    return temp


def survfit0(x):
    """Return ``x`` with a time-zero row added to each curve.

    Objects that already start at time zero, or are already survfit0, are
    returned unchanged.
    """
    if not _inherits(x, "survfit"):
        raise ValueError("function requires a survfit object")
    if _inherits(x, "survfit0") or bool(x.get("time0")):
        return x

    time = np.asarray(x["time"], dtype=float)
    t0 = x.get("t0")
    if t0 is None:  # ordinary survival
        t0 = min(0.0, float(np.min(time))) if time.size else 0.0

    # insert = 0-based row where each curve starts
    strata = x.get("strata")
    if strata is None:
        insert = np.array([0], dtype=int)
    else:
        strata = np.asarray(strata, dtype=int)
        insert = np.concatenate([[0], np.cumsum(strata[:-1])]).astype(int)

    same = time[insert] == t0  # the curve already starts at t0
    insert = insert[~same]
    if insert.size == 0:
        return x

    newstrat = None
    if strata is not None:
        newstrat = strata.copy()
        newstrat[~same] += 1

    new = {key: value for key, value in x.items() if key != "sp0"}

    p00 = None
    if x.get("p0") is not None:  # multi-state
        p0 = np.asarray(x["p0"], dtype=float)
        sp0 = 0.0 if x.get("sp0") is None else x["sp0"]
        if np.any(same):
            p00 = p0[~same, :]
            if x.get("sp0") is not None:
                sp0 = np.asarray(x["sp0"], dtype=float)[~same, :]
        else:
            p00 = p0
    else:
        # R checks x$xtd.err here, which never exists; sp0 is always 0.
        if x.get("xtd.err") is not None:
            sp0 = np.asarray(x["std.err"], dtype=float)[insert, :]
        else:
            sp0 = 0.0

    survfitms = _inherits(x, "survfitms")
    add1 = ["surv"]
    add0 = ["n.event", "n.censor", "n.enter", "n.transition", "cumhaz", "std.chaz", "std.auc"]
    if survfitms:
        add0 += ["lower", "upper"]
    else:
        add1 += ["lower", "upper"]

    for name in list(new.keys()):
        if name == "time":
            new[name] = _addto(x["time"], insert, t0)
        elif name == "n.risk":
            nr = np.asarray(x["n.risk"], dtype=float)
            new[name] = _addto(nr, insert, nr[insert, :] if nr.ndim == 2 else nr[insert])
        elif name == "pstate":
            if p00 is None:
                raise ValueError("pstate without p0 is not a valid survfitms object")
            new[name] = _addto(x["pstate"], insert, p00)
        elif name == "strata":
            new[name] = newstrat
        elif name == "std.err":
            new[name] = _addto(x["std.err"], insert, sp0)
        elif name in add0:
            new[name] = _addto(x[name], insert, 0.0)
        elif name in add1:
            new[name] = _addto(x[name], insert, 1.0)

    if not survfitms:
        for name in ("influence.surv", "influence.chaz"):
            if x.get(name) is not None:
                value = x[name]
                if isinstance(value, list):
                    new[name] = [_addcol(item) for item in value]
                else:
                    new[name] = _addcol(value)
    elif x.get("influence") is not None:  # multi-state influence
        influence = x["influence"]
        if isinstance(influence, list):
            i0 = x.get("i0")
            if i0 is None:
                new["influence"] = [_addi0(item) for item in influence]
            else:
                new["influence"] = [_addi0(item, i0[k]) for k, item in enumerate(influence)]
        else:
            new["influence"] = _addi0(influence, x.get("i0"))

    x = dict(x)  # R sets x$logse on a local copy
    if new.get("logse") is None:
        x["logse"] = not survfitms

    if x.get("cumhaz") is None and _classes(x)[0] == "survfit":
        new["cumhaz"] = -np.log(np.asarray(new["surv"], dtype=float))
        if x.get("std.err") is not None:
            if x["logse"]:
                new["std.chaz"] = new["std.err"]
            else:
                new["std.chaz"] = np.asarray(new["std.err"]) / np.asarray(new["surv"])

    new["class_"] = ("survfit0", *_classes(x))
    return new
