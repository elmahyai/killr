"""R-level wrappers for the logspline 2.1.22 objects and methods."""

from __future__ import annotations

import io
import math
from contextlib import redirect_stdout
from typing import Any

import numpy as np


def _kernel():
    import importlib
    import sys
    crate = importlib.import_module("logspline")
    # When this translated package is on sys.path it shadows the same-named
    # maturin extension.  Load the extension temporarily under its required
    # module name in that uncommon layout.
    if callable(getattr(crate, "rpqlsd", None)) and getattr(crate.rpqlsd, "__module__", "") == __name__:
        from pathlib import Path
        from importlib.util import module_from_spec, spec_from_file_location
        for root in map(Path, sys.path):
            if not root.is_dir():
                continue
            candidates = list(root.glob("logspline*.so"))
            candidates += list(root.glob("logspline/logspline*.so"))
            if candidates:
                old = sys.modules.pop("logspline", None)
                spec = spec_from_file_location("logspline", candidates[0])
                ext = module_from_spec(spec)
                sys.modules["logspline"] = ext
                try:
                    spec.loader.exec_module(ext)
                    return ext
                finally:
                    sys.modules["logspline"] = old
        raise ImportError("the logspline Rust extension is not installed")
    return crate


def unstrip(x: Any):
    """Remove R's strip attributes while retaining a matrix's dimensions."""
    a = np.asarray(x)
    if a.ndim <= 1:
        return a.reshape(-1).copy()
    if a.ndim == 2:
        return a.copy()
    return a.reshape(-1).copy()


def _get(x: Any, key: str, default=None):
    return x.get(key, default) if isinstance(x, dict) else getattr(x, key, default)


def _old_to_new(obj: Any, data=None) -> dict[str, Any]:
    coef = np.asarray(_get(obj, "coef"), dtype=float).reshape(-1)
    knots0 = np.asarray(_get(obj, "knots"), dtype=float).reshape(-1)
    ck = coef[2:]
    used = ck != 0
    out: dict[str, Any] = {
        "call": _get(obj, "call") or "translated from oldlogspline",
        "knots": int(np.sum(used)),
        "coef.pol": coef[:2],
        "coef.kts": ck[used],
        "maxknots": len(coef) - 2,
        "penalty": _get(obj, "penalty"),
        "bound": _get(obj, "bound"),
        "samples": _get(obj, "sample"),
    }
    out["knots"] = knots0[used]
    ll = np.asarray(_get(obj, "logl"), dtype=float).reshape(-1)
    ll = ll[ll != 0]
    out["logl"] = np.column_stack(
        [out["maxknots"] + 1 - np.arange(len(ll), 0, -1),
         np.r_[np.repeat(2, max(0, len(ll) - 1)), 1], ll]
    )
    if data is not None:
        out["range"] = _get(obj, "range")
    else:
        s = float(out["samples"])
        out["range"] = qlogspline([1 / (s + 1), 1 - 1 / (s + 1)], out)
    return out


def _sorted_restore(values, calculated):
    a = np.asarray(values)
    flat = a.reshape(-1)
    order = np.argsort(flat, kind="mergesort")
    out = np.empty_like(np.asarray(calculated, dtype=float))
    out[order] = np.asarray(calculated, dtype=float)
    return out.reshape(a.shape)


def qlogspline(p, fit):
    p = unstrip(p)
    vals = p.reshape(-1).astype(float)
    z = _kernel().rpqlsd(
        np.r_[np.asarray(_get(fit, "coef.pol"), float),
              np.asarray(_get(fit, "coef.kts"), float)],
        np.asarray(_get(fit, "knots"), float),
        np.asarray(_get(fit, "bound"), float),
        0, np.sort(vals), len(np.asarray(_get(fit, "knots"))), len(vals),
    )
    result = _sorted_restore(vals, z.get("pq", z.get("qq")))
    result[vals < 0] = np.nan
    result[vals > 1] = np.nan
    return result


def qoldlogspline(p, fit):
    return qlogspline(p, _old_to_new(fit))


def rlogspline(n, fit):
    return qlogspline(np.random.random(int(n)), fit)


def roldlogspline(n, fit):
    if _get(fit, "class", "oldlogspline") not in ("oldlogspline", None):
        raise TypeError("fit is not an oldlogspline object")
    return qoldlogspline(np.random.random(int(n)), fit)


def _summary_table(fit, old=False):
    ul = float(_get(fit, "penalty"))
    samples = _get(fit, "sample") if old else _get(fit, "samples")
    if old:
        um = float(samples)
    else:
        samples = np.asarray(samples).reshape(-1)
        um = float(samples[0] + samples[3]) if samples.size > 3 else float(samples[0])
    ll = np.asarray(_get(fit, "logl"), float)
    if old:
        ll = ll[ll != 0]
        kk = np.arange(1, len(ll) + 1, dtype=float) + 2
        ad = None
    else:
        ll = ll[ll[:, 1] != 0]
        kk, ad, ll = ll[:, 0], ll[:, 1], ll[:, 2]
    bb = -2 * ll + ul * (kk if old else kk - 1)
    c1, c2 = bb.copy(), bb.copy()
    c2[0] = np.inf if not old else np.inf
    c1[-1] = 0
    for i in range(len(bb) - 1):
        c1[i] = np.max((ll[i + 1:] - ll[i]) / (kk[i + 1:] - kk[i]))
        c2[i + 1] = np.min((ll[:i + 1] - ll[i + 1]) / (kk[:i + 1] - kk[i + 1]))
    bad = c2 - c1 < 0
    c1[bad] = np.nan
    c2[bad] = np.nan
    return kk, ad, ll, bb, c1, c2, um, ul


def summary_logspline(object_, **_):
    kk, ad, ll, bb, c1, c2, um, ul = _summary_table(object_)
    rows = np.column_stack([kk, ad, ll, bb, 2 * c1, 2 * c2])
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(np.array2string(np.round(rows, 2), separator=" "))
        print(f"the present optimal number of knots is  {kk[bb == np.min(bb)]}")
        if ul == math.log(um):
            print(f"penalty(AIC) was the default: BIC=log(samplesize): log( {um:g} )={round(ul, 2):g}")
        else:
            print(f"penalty(AIC) was  {ul:.2f}, the default (BIC)  would have been {math.log(um):.2f}")
    return buf.getvalue()


def summary_oldlogspline(object_, **_):
    if _get(object_, "delete", True) is False:
        raise ValueError("summary.oldlogspline can only provide information if delete in oldlogspline is TRUE")
    kk, _, ll, bb, c1, c2, um, ul = _summary_table(object_, old=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(np.array2string(np.round(np.column_stack([kk, ll, bb, 2*c1, 2*c2]), 2), separator=" "))
        print(f"the present optimal number of knots is  {kk[bb == np.min(bb)]}")
        if ul == math.log(um):
            print(f"penalty(AIC) was the default: BIC=log(samplesize): log( {um:g} )={round(ul, 2):g}")
        else:
            print(f"penalty(AIC) was  {ul:.2f}, the default (BIC)  would have been {math.log(um):.2f}")
    return buf.getvalue()


def print_logspline(x, **kwargs):
    text = summary_logspline(x, **kwargs)
    print(text, end="")
    return x


def print_oldlogspline(x, **kwargs):
    text = summary_oldlogspline(x, **kwargs)
    print(text, end="")
    return x


def rpqlsd(coef, knots, bnd, ipq, pq, lk=None, lp=None):
    """Thin Python spelling of the Rust kernel entry point."""
    a = np.asarray(pq, dtype=float)
    return _kernel().rpqlsd(np.asarray(coef, float), np.asarray(knots, float),
                            np.asarray(bnd, float), int(ipq), a,
                            len(np.asarray(knots)) if lk is None else int(lk),
                            len(a) if lp is None else int(lp))


qlogspline.__name__ = "qlogspline"
qoldlogspline.__name__ = "qoldlogspline"
summary_logspline.__name__ = "summary.logspline"
summary_oldlogspline.__name__ = "summary.oldlogspline"
print_logspline.__name__ = "print.logspline"
print_oldlogspline.__name__ = "print.oldlogspline"

