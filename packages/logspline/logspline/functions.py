"""Python translation of the logspline R wrappers.

The numerical work remains in the sibling ``logspline`` Rust extension; this
module mirrors the R object layouts and wrapper semantics.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import importlib

try:
    # The maturin extension is the ``logspline.logspline`` submodule.  Import
    # it explicitly so a source namespace directory cannot shadow it.
    _kernel = importlib.import_module("logspline.logspline")
except ImportError:  # useful with older top-level maturin installations
    _kernel = importlib.import_module("logspline")


def _a(x, dtype=float):
    return np.asarray(x, dtype=dtype).reshape(-1)


def _unstrip(x):
    return np.asarray(x).reshape(-1)


def _bounds(lbound=None, ubound=None):
    return [int(lbound is not None), 0.0 if lbound is None else float(lbound),
            int(ubound is not None), 0.0 if ubound is None else float(ubound)]


def nlogcensorx(z):
    return _kernel.nlogcensorx(_a(z, np.int32))


def nlogcensor(ip, coef, dp, logl, ad, kts):
    return _kernel.nlogcensor(_a(ip, np.int32), _a(coef), _a(dp), _a(logl),
                              _a(ad, np.int32), _a(kts))


def rpqlsd(coef, knots, bnd, ipq, pq, lk, lp):
    return _kernel.rpqlsd(_a(coef), _a(knots), _a(bnd), int(ipq), _a(pq),
                          int(lk), int(lp))


def logcensor(delete, iautoknot, sample, nsample, bd, sorc, nk, kt, cf,
              penalty, wk, wk2, logl):
    return _kernel.logcensor(_a(delete, np.int32), _a(iautoknot, np.int32),
                             _a(sample), _a(nsample, np.int32), _a(bd),
                             _a(sorc, np.int32), int(nk), _a(kt), _a(cf),
                             _a(penalty), _a(wk), _a(wk2), _a(logl))


def _fit_arrays(fit):
    return (_a(fit["coef.pol"]).tolist() + _a(fit["coef.kts"]).tolist(),
            _a(fit["knots"]), _a(fit["bound"]))


def plogspline(q, fit):
    q0 = _unstrip(q).astype(float)
    order = np.argsort(q0, kind="mergesort")
    qs = q0[order]
    coef, knots, bnd = _fit_arrays(fit)
    out = rpqlsd(coef, knots, bnd, 1, qs, len(knots), len(qs))["pq"]
    ans = np.empty_like(qs)
    ans[order] = out
    if bnd[0] > 0:
        ans[q0 < bnd[1]] = 0.0
    if bnd[2] > 0:
        ans[q0 > bnd[3]] = 1.0
    return ans.reshape(np.asarray(q).shape)


def qlogspline(p, fit):
    p0 = _unstrip(p).astype(float)
    order = np.argsort(p0, kind="mergesort")
    ps = p0[order]
    coef, knots, bnd = _fit_arrays(fit)
    out = rpqlsd(coef, knots, bnd, 0, ps, len(knots), len(ps))["pq"]
    ans = np.empty_like(ps)
    ans[order] = out
    ans[(p0 < 0) | (p0 > 1)] = np.nan
    return ans.reshape(np.asarray(p).shape)


def dlogspline(q, fit, log=False):
    x = _unstrip(q).astype(float)
    y = float(_a(fit["coef.pol"])[0]) + x * float(_a(fit["coef.pol"])[1])
    for c, k in zip(_a(fit["coef.kts"]), _a(fit["knots"])):
        y += c * (np.maximum(x - k, 0.0)) ** 3
    b = _a(fit["bound"])
    y[(b[0] > 0) & (x < b[1])] = -np.inf
    y[(b[2] > 0) & (x > b[3])] = -np.inf
    return y if log else np.exp(y)


def _new_fit(x, lbound=None, ubound=None, maxknots=0, knots=None,
             nknots=0, penalty=-1, silent=True, mind=-1, error_action=2):
    data = _unstrip(x).astype(float)
    data = data[~np.isnan(data)]
    if data.size < 10 or np.unique(data).size < 3:
        raise ValueError("not enough data")
    data.sort()
    ilow, iupp = int(lbound is not None), int(ubound is not None)
    low = 0.0 if lbound is None else float(lbound)
    upp = 0.0 if ubound is None else float(ubound)
    maxp = int(nlogcensorx(np.r_[-100, np.zeros(9, dtype=np.int32)])["z"][0])
    given = None if knots is None else np.sort(_unstrip(knots).astype(float))
    if given is not None:
        nknots = len(given)
        if nknots < 3:
            raise ValueError("need at least three starting knots")
    else:
        nknots = -int(nknots)
    kts = np.zeros(maxp)
    if given is not None:
        kts[:len(given)] = given
    ip = np.array([len(data), maxknots, nknots, int(not silent),
                   1 - ilow, 1 - iupp, int(mind)], dtype=np.int32)
    dp = np.array([math.log(len(data)) if penalty == -1 else penalty, low, upp])
    z = nlogcensor(ip, np.r_[data, np.zeros(maxp)], dp,
                   np.zeros(maxp), np.zeros(maxp, dtype=np.int32), kts)
    nk = int(z["ip"][1])
    lx = np.column_stack((z["ad"][1:int(z["ip"][2]) + 1],
                          z["logl"][1:int(z["ip"][2]) + 1]))
    lx = np.column_stack((2 + np.arange(len(lx)), lx))
    lx = lx[lx[:, 1] != 0]
    mm = np.array([min(data.min(), low) if ilow else data.min(),
                   max(data.max(), upp) if iupp else data.max()])
    return {"call": None, "nknots": nk, "coef.pol": z["coef"][:2],
            "coef.kts": z["coef"][2:nk + 2], "knots": z["kts"][:nk],
            "maxknots": int(z["ip"][2]) + 2, "penalty": z["dp"][0],
            "bound": np.array([ilow, low, iupp, upp]), "samples": np.array([len(data)]),
            "logl": lx, "range": mm, "mind": z["ip"][6], "_class": "logspline"}


def logspline(x, lbound=None, ubound=None, maxknots=0, knots=None,
              nknots=0, penalty=-1, silent=True, mind=-1, error_action=2):
    return _new_fit(x, lbound, ubound, maxknots, knots, nknots, penalty,
                    silent, mind, error_action)


def oldlogspline(uncensored=None, right=None, left=None, interval=None,
                 lbound=None, ubound=None, nknots=None, knots=None,
                 penalty=None, delete=True):
    u = np.array([]) if uncensored is None else _unstrip(uncensored).astype(float)
    u = u[~np.isnan(u)]
    sample = u.tolist()
    ns = [len(u), len(u), 0, 0, 0, np.unique(u).size]
    if interval is not None:
        iv = np.asarray(interval, float).reshape(-1, 2)
        if lbound is not None: iv[:, 0] = np.maximum(iv[:, 0], lbound)
        if ubound is not None: iv[:, 1] = np.minimum(iv[:, 1], ubound)
        sample.extend(iv.ravel()); ns[0] += len(iv); ns[2] = len(iv)
    for vals, pos in ((right, 3), (left, 4)):
        if vals is not None:
            v = _unstrip(vals).astype(float); sample.extend(v)
            ns[pos] = len(v); ns[0] += len(v)
    if ns[0] == 0: raise ValueError("you need uncensored or interval censored data")
    if penalty is None: penalty = math.log(ns[0])
    auto = knots is None
    kk = 0 if nknots is None else int(nknots)
    ks = np.zeros(max(50, kk)) if auto else np.sort(_unstrip(knots).astype(float))
    if not auto: kk = len(ks)
    s = np.asarray(sample, float)
    z = logcensor([int(delete)], [int(auto)], np.r_[s, np.zeros(4)],
                  np.r_[ns, np.zeros(4)], [1, 0, 0, 0, 0], np.r_[1, np.zeros(34)],
                  kk, np.r_[ks, np.zeros(4)], np.r_[ks, np.zeros(4)],
                  [penalty], np.r_[s, np.zeros(4)], np.r_[s, np.zeros(4)],
                  np.zeros(4 * ns[0] ** .2 + 12))
    nk = int(z["nk"])
    return {"coef": z["cf"][:nk + 2], "knots": z["kt"][:nk],
            "bound": z["bd"][1:5], "logl": z["logl"], "penalty": penalty,
            "sample": ns[0], "delete": delete, "_class": "oldlogspline",
            "range": np.array([s.min(), s.max()])}


def oldlogspline_to_logspline(obj, data=None):
    nz = {"call": obj.get("call", "translated from oldlogspline"),
          "coef.pol": _a(obj["coef"])[:2], "coef.kts": _a(obj["coef"])[2:],
          "knots": _a(obj["knots"])[_a(obj["coef"])[2:] != 0],
          "maxknots": len(obj["coef"]) - 2, "penalty": obj["penalty"],
          "bound": obj["bound"], "samples": np.array([obj["sample"]]),
          "mind": None, "_class": "logspline"}
    ll = _a(obj["logl"]); nz["logl"] = np.column_stack((nz["maxknots"] + 1 - np.arange(len(ll), 0, -1),
                                                         np.r_[np.repeat(2, max(len(ll)-1, 0)), 1], ll))
    nz["range"] = obj.get("range", qlogspline([1/(obj["sample"]+1), 1-1/(obj["sample"]+1)], nz))
    return nz


def poldlogspline(q, fit): return plogspline(q, oldlogspline_to_logspline(fit))
def doldlogspline(q, fit):
    return dlogspline(q, oldlogspline_to_logspline(fit))


def plot_logspline(x, n=100, what="d", add=False, xlim=None, xlab="", ylab="", type="l", **kwargs):
    import matplotlib.pyplot as plt
    if xlim is None:
        u1, u2 = qlogspline([.01, .99], x); xlim = (1.1*u1-.1*u2, 1.1*u2-.1*u1)
    xx = np.linspace(*xlim, n)
    yy = dlogspline(xx, x) if what.lower() == "d" else plogspline(xx, x)
    if what.lower() == "s": yy = 1 - plogspline(xx, x)
    if what.lower() == "h": yy = dlogspline(xx, x) / (1 - plogspline(xx, x))
    if not add: plt.plot(xx, yy, label=ylab or None, **kwargs)
    else: plt.plot(xx, yy, **kwargs)
    return {"x": xx, "y": yy}


def plot_oldlogspline(x, **kwargs): return plot_logspline(oldlogspline_to_logspline(x), **kwargs)

