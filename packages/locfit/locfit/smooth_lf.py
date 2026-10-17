"""smooth.lf(): R's local smooth with (x, y) input and mu-hat output.

R (locfit 1.5-9.12):

    smooth.lf <- function(x, y, xev = x, direct = FALSE, ...) {
      if (missing(y)) { y <- x; x <- 1:length(y) }
      if (direct) {
        fit <- locfit.raw(x, y, ev = xev, geth = 7, ...)
        fv <- fit$y; xev <- fit$x
      } else {
        fit <- locfit.raw(x, y, ...)
        fv <- predict(fit, xev)
      }
      list(x = xev, y = fv, call = match.call())
    }

The default path (``direct = FALSE``) fits ``locfit.raw`` on R's default
``ev = rbox()`` kd-tree and reads the values with ``predict``. ``predict`` at
the data points is the tree fit's fitted values, so the default ``xev = x``
is ``fitted`` from ``crates/locfit``. ``predict`` at other points needs the
tree interpolation, which ``crates/locfit`` does not expose; those calls raise.
``direct = TRUE`` uses locfit's ``geth = 7`` smoother, which is not in
``crates/locfit``; it raises too.
"""

from __future__ import annotations

import numpy as np

try:
    from ..locfit_raw import locfit_raw, fitted
except ImportError:  # loaded by file path, with packages/locfit on sys.path
    from locfit_raw import locfit_raw, fitted


def smooth_lf(x, y=None, xev=None, direct=False, **kwargs):
    if y is None:
        y = x
        x = np.arange(1, len(np.asarray(y)) + 1, dtype=float)
    if direct:
        raise NotImplementedError(
            "smooth.lf(direct = TRUE) uses locfit.raw geth = 7 (simple smoother), "
            "not in crates/locfit")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    fit = locfit_raw(x, y, **kwargs)
    if xev is None:
        xev = x
    xe = np.asarray(xev, dtype=float)
    if xe.shape != x.shape or not np.array_equal(xe, x):
        raise NotImplementedError(
            "smooth.lf: predict on the rbox() tree at new points (tree interpolation) "
            "is not in crates/locfit; use xev equal to x")
    fv = fitted(fit)
    return {"x": xev, "y": fv, "call": "smooth.lf"}


__all__ = ["smooth_lf"]
