"""`imputeData` of mclust 6.1.3 (R/impute.R), the function that calls the mix package.

The R function imputes a data set by the mixed-data model of mix: categorical columns
and continuous columns. It fits the model by EM, draws the parameters by 100 steps of
data augmentation, and imputes under the last draw. The generator is re-seeded and the
imputation is repeated once, as the R code does.

Two kinds of input are accepted:

* A numeric array (rows are cases, columns are variables). A categorical column is given
  as its positive integer codes, which is the contract of mix's `prelim.mix`.
* A data frame, given as a mapping from column name to column (in column order). A
  column is a numeric sequence, a `Factor`, or a sequence of text labels. The data frame
  is turned into the matrix R builds in `as.matrix`, and then imputed the same way:

  - `categorical=None`: R's `apply(data, 2, is.factor)` reads the `as.matrix` of the data
    frame, which holds no factor, so no column is categorical. The dummy column is added,
    and every numeric column goes through `as.matrix`'s `format()`, which keeps seven
    significant digits. A factor column is read as its labels, which are numbers here.
  - `categorical` given: R converts every column with `as.factor`, so a numeric column is
    read from its 15-digit text, and a categorical column is read as the integer part of
    its label (`as.integer`). A label that is not a number becomes NA.

Differences from the R function that remain:

* With `seed=None` the seed is drawn from the same interval as R's `runif`, but from
  Python's generator, so the draw differs from R's stream. Pass `seed` for a result
  that can be compared with R.
* R's `format()` chooses fixed or scientific layout and rounds with long double. This
  port rounds with the correctly rounded decimal conversion of the C library, which
  agrees except in rare exact ties at the seventh digit.
* R returns the categorical columns as their integer codes, not as factor labels. This
  port does the same. A label that is not a number is NA in R, and a column with no
  observed number stops R with an error, which this port raises as a ValueError.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping

import numpy as np

from .da_mix import da_mix
from .em_mix import em_mix
from .imp_mix import imp_mix
from .prelim_mix import prelim_mix
from .rngseed import rngseed

# options("digits") in R, used by format() in as.matrix
_R_DIGITS = 7
# R's KP_MAX, the largest power of ten in the rounding-widens test
_KP_MAX = 22


class Factor:
    """An R factor column. `labels` are the level labels of each case; None is NA."""

    def __init__(self, labels):
        self.labels = [_label_text(v) for v in labels]


def _label_text(v):
    """The text R's as.character gives for one element, or None for NA."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, (float, np.floating)):
        if math.isnan(v):
            return None
        return "%.15g" % float(v)
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return str(v)


def _parse_number(text):
    """as.double of one text label: a number, or NaN (NA) when it is not one."""
    if text is None:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def _r_format_digits(x):
    """Values of R's format(x, digits = 7) read back by as.numeric.

    The layout is R's formatReal: each element needs some number of significant digits
    (at most seven) and some number of decimals; the column uses the largest decimal
    count, and fixed notation unless scientific is narrower. NaN stays NaN and infinities
    pass through.
    """
    x = np.asarray(x, dtype=float)
    finite = np.isfinite(x)
    out = x.copy()
    if not finite.any():
        return out

    any_neg = False
    rgt = -math.inf
    mxl = -math.inf
    mxsl = -math.inf
    mxns = -math.inf
    mxe = -math.inf
    mne = math.inf
    for v in x[finite]:
        if v == 0.0:
            kpower, nsig, neg, widens = 0, 1, 0, False
        else:
            neg = 1 if v < 0 else 0
            mant, _, expo = ("%.*e" % (_R_DIGITS - 1, abs(v))).partition("e")
            kpower = int(expo)
            nsig = len(mant.replace(".", "").rstrip("0")) or 1
            widens = 0 < kpower <= _KP_MAX and abs(v) < 10.0 ** kpower
        left = kpower + 1 - (1 if widens else 0)
        sleft = neg + (1 if left <= 0 else left)
        right = nsig - left
        any_neg = any_neg or bool(neg)
        rgt = max(rgt, right)
        mxl = max(mxl, left)
        mxsl = max(mxsl, sleft)
        mxns = max(mxns, nsig)
        mxe = max(mxe, kpower)
        mne = min(mne, kpower)

    if mxl < 0:
        mxsl = 1 + int(any_neg)
    rgt = max(int(rgt), 0)
    width_f = int(mxsl) + rgt + (1 if rgt else 0)
    expo_digits = 2 if (mxe >= 100 or mne <= -99) else 1
    d = int(mxns) - 1
    width_e = int(any_neg) + (1 if d > 0 else 0) + d + 4 + expo_digits
    fixed = width_f <= width_e

    for k in np.flatnonzero(finite):
        v = float(x[k])
        text = ("%.*f" % (rgt, v)) if fixed else ("%.*e" % (d, v))
        out[k] = float(text)
    return out


def _r_round_label(x):
    """Values after as.character (15 significant digits) and as.double."""
    x = np.asarray(x, dtype=float)
    out = x.copy()
    for k in np.flatnonzero(np.isfinite(x)):
        out[k] = float("%.15g" % float(x[k]))
    return out


def _column_as_matrix(col, digits):
    """One column as the numbers R's as.matrix leaves in it, with NA as NaN.

    `digits=True` is the path where the data frame is formatted (no categorical column):
    numeric columns are formatted to seven significant digits. `digits=False` is the path
    where every column is a factor: numeric columns come back through their 15-digit text.
    """
    if isinstance(col, Factor):
        return np.array([_parse_number(t) for t in col.labels], dtype=float)

    arr = np.asarray(col)
    if arr.dtype.kind == "b":
        raise TypeError("logical columns are not supported by imputeData")
    if arr.dtype.kind == "O" and not all(
        v is None or (isinstance(v, (int, float, np.number)) and not isinstance(v, bool))
        for v in arr
    ):
        return np.array([_parse_number(_label_text(v)) for v in arr], dtype=float)
    if arr.dtype.kind in "US":
        return np.array([_parse_number(_label_text(v)) for v in arr], dtype=float)

    if arr.dtype.kind in "iu":
        return arr.astype(float)  # R's integer format is exact

    values = np.array(
        [math.nan if v is None else float(v) for v in arr.ravel()], dtype=float
    )
    if digits:
        return _r_format_digits(values)
    return _r_round_label(values)


def _data_frame_matrix(columns, categorical):
    """The numeric matrix and categorical flags that R's imputeData builds for a data frame."""
    cols = list(columns.values())
    if not cols:
        raise ValueError("data has no columns")
    lengths = {len(c.labels) if isinstance(c, Factor) else len(np.asarray(c)) for c in cols}
    if len(lengths) != 1:
        raise ValueError("all columns must have the same length")

    if categorical is None:
        # apply(data, 2, is.factor) on the as.matrix of a data frame is FALSE everywhere
        out = [_column_as_matrix(c, digits=True) for c in cols]
        cat = np.zeros(len(cols), dtype=bool)
    else:
        cat = _categorical_mask(categorical, len(cols))
        out = []
        for j, c in enumerate(cols):
            v = _column_as_matrix(c, digits=False)
            if cat[j]:
                # storage.mode "integer" truncates toward zero
                v = np.trunc(v)
            out.append(v)
    for j, v in enumerate(out):
        if not np.isfinite(v).any():
            # R stops here: a column with no observed value gives NA in its centring step
            raise ValueError("column %d has no observed value that is a number" % (j + 1))
    return np.column_stack(out), cat


def _categorical_mask(categorical, nvar):
    if categorical is None:
        return np.zeros(nvar, dtype=bool)
    cat = np.asarray(categorical, dtype=bool).ravel()
    if cat.shape != (nvar,):
        raise ValueError("categorical must have one entry per column")
    return cat


def imputeData(data, categorical=None, seed=None, verbose: bool = False):
    if isinstance(data, Mapping):
        x, cat = _data_frame_matrix(data, categorical)
    else:
        x = np.asarray(data, dtype=float)
        if x.ndim == 1:
            x = x.reshape(-1, 1)
        cat = _categorical_mask(categorical, x.shape[1])
    return _impute(x, cat, seed, verbose)


def _impute(x, cat, seed, verbose):
    nocat = not cat.any()
    if nocat:
        # cbind(as.factor(1), data): a dummy categorical column of ones
        x = np.column_stack([np.ones(x.shape[0]), x])
        cat = np.r_[True, cat]

    order = np.r_[np.flatnonzero(cat), np.flatnonzero(~cat)]  # ord, 0-based

    # do the imputations
    s = prelim_mix(x[:, order], p=int(cat.sum()))
    if seed is None:
        seed = random.uniform(2147483647 / 1024, 2147483647)
    # find ML estimate
    thetahat = em_mix(s, showits=verbose)
    # set random number generator seed
    rngseed(seed)
    # data augmentation from posterior
    newtheta = da_mix(s, thetahat, steps=100, showits=verbose)
    # impute under newtheta
    dataimp = imp_mix(s, newtheta)
    # there is a bug, so it needs to refix the seed and impute again
    rngseed(seed)
    dataimp = imp_mix(s, newtheta)

    if nocat:
        out = dataimp[:, 1:]
    else:
        out = dataimp[:, np.argsort(order)]
    # R drops a single column to a vector
    if out.shape[1] == 1:
        return out[:, 0]
    return out
