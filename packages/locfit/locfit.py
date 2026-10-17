"""locfit: R's locfit() formula front end, on top of locfit_raw.

Supports ``"y ~ x1 + x2"`` with a mapping (or data frame) ``data``. Weights,
cens and base may be values or column names. Interaction and other formula
terms are not translated. The fit is produced by ``lfproc``, which defaults
to ``locfit_raw``, as in R.
"""

from __future__ import annotations

import numpy as np

from .locfit_raw import locfit_raw


def _lookup(arg, data):
    return data[arg] if isinstance(arg, str) else arg


def locfit(formula, data, weights=1, cens=0, base=0, subset=None, geth=0,
           lfproc=None, **kwargs):
    if not isinstance(formula, str) or "~" not in formula:
        raise TypeError("locfit needs a formula string such as 'y ~ x'")
    if subset is not None:
        raise NotImplementedError("subset is not translated")
    lhs, rhs = (s.strip() for s in formula.split("~", 1))
    terms = [t.strip() for t in rhs.split("+")]
    for t in terms:
        if not t or t == "." or any(ch in t for ch in "*:()"):
            raise NotImplementedError(f"formula term {t!r} is not translated")
    y = np.asarray(data[lhs], dtype=float)
    x = np.column_stack([np.asarray(data[t], dtype=float) for t in terms])
    proc = locfit_raw if lfproc is None else lfproc
    ret = proc(x, y, weights=_lookup(weights, data), cens=_lookup(cens, data),
               base=_lookup(base, data), geth=geth, **kwargs)
    ret["call"] = "locfit"
    ret["yname"] = lhs
    ret["vnames"] = terms
    return ret
