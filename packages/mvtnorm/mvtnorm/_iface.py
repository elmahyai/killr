"""``mvnorm`` model methods for mvtnorm 1.4-2.

Triangular helpers are the callables in ``mvtnorm._lt`` (see ``mvtnorm._lp``).
This module does not import ``_lt`` itself; ``_lp._fun`` loads it on first use.
"""

from __future__ import annotations

import numpy as np

from extradistr._rng import norm_rand

from mvtnorm._lp import (
    MISSING,
    _as_mat,
    _byrow,
    _diag,
    _dim,
    _fun,
    _is_lt,
    _matnames,
    _rcnames,
    _seed_guard,
    _stop,
    _unclass,
    deperma,
    destandardize,
    ldpmvnorm,
    r_add,
    r_matrix,
    r_sub,
    sldpmvnorm,
    standardize as _standardize,
)


class _RMatrix(np.ndarray):
    """Numeric matrix that can carry R row and column names."""

    def __new__(cls, data, rownames=None, colnames=None):
        obj = np.array(data, dtype=float, copy=True).view(cls)
        obj.rownames = None if rownames is None else list(rownames)
        obj.colnames = None if colnames is None else list(colnames)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.rownames = getattr(obj, "rownames", None)
        self.colnames = getattr(obj, "colnames", None)


class Coef(_RMatrix):
    """Coefficient vector or matrix with an R ``sigma`` attribute."""

    def __new__(cls, data, sigma=None, rownames=None, colnames=None):
        obj = np.array(data, dtype=float, copy=True).view(cls)
        obj.rownames = None if rownames is None else list(rownames)
        obj.colnames = None if colnames is None else list(colnames)
        obj.sigma = None if sigma is None else np.asarray(sigma, dtype=float).ravel()
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.rownames = getattr(obj, "rownames", None)
        self.colnames = getattr(obj, "colnames", None)
        self.sigma = getattr(obj, "sigma", None)


class Mvnorm:
    """An ``mvnorm`` object: a Cholesky scale and an optional mean."""

    def __init__(self, scale, mean=None, invcholmean=None):
        self.scale = scale
        self.mean = mean
        self.invcholmean = invcholmean

    def logLik(self, obs=MISSING, lower=MISSING, upper=MISSING, standardize=False, **kwargs):
        return logLik_mvnorm(self, obs, lower, upper, standardize, **kwargs)

    def simulate(self, nsim=None, seed=None, standardize=False, as_data_frame=False, **kwargs):
        return simulate_mvnorm(self, nsim, seed, standardize, as_data_frame, **kwargs)

    def mean(self, **kwargs):
        return mean_mvnorm(self, **kwargs)

    def vcov(self, **kwargs):
        return vcov_mvnorm(self, **kwargs)

    def coef(self, which=None, **kwargs):
        return coef_mvnorm(self, which, **kwargs)


def _nrow(x) -> int:
    a = np.asarray(x)
    if a.ndim == 0:
        return 1
    return int(a.shape[0])


def _ncol(x) -> int:
    a = np.asarray(x)
    if a.ndim <= 1:
        return 1
    return int(a.shape[1])


def _is_matrix(x) -> bool:
    return isinstance(x, np.ndarray) and x.ndim == 2


def _row_names(x):
    val = getattr(x, "rownames", None)
    if val is None:
        val = getattr(x, "names", None)
    if val is None:
        return None
    return list(val)


def _col_names(x):
    val = getattr(x, "colnames", None)
    if val is None:
        return None
    return list(val)


def _named_matrix(data, nrow, ncol, rownames=None, colnames=None):
    arr = r_matrix(data, nrow=nrow, ncol=ncol)
    return _RMatrix(arr, rownames=rownames, colnames=colnames)


def _positions(which, names, J):
    """1-based positions. Negative indexes are kept negative, as in R."""
    if isinstance(which, str):
        items = [which]
    elif isinstance(which, (list, tuple)) and which and isinstance(which[0], str):
        items = list(which)
    else:
        arr = np.atleast_1d(np.asarray(which))
        if arr.dtype.kind in "USO":
            items = [str(v) for v in arr]
        else:
            return [int(v) for v in arr.ravel()]
    if names is None:
        _stop("missing names")
    return [list(names).index(item) + 1 for item in items]


def _rows(mat, which, drop):
    """R ``mat[which, , drop]``. ``which`` is 1-based, and may be negative."""
    mat = np.asarray(mat, dtype=float)
    if mat.ndim == 1:
        mat = mat.reshape((-1, 1), order="F")
    idx = [int(i) for i in np.atleast_1d(np.asarray(which)).ravel()]
    if any(i < 0 for i in idx):
        drop_at = {-i - 1 for i in idx if i < 0}
        keep = [i for i in range(mat.shape[0]) if i not in drop_at]
        sub = mat[keep, :]
    else:
        sub = mat[[i - 1 for i in idx], :]
    rn = _row_names(mat)
    if rn is not None:
        if any(i < 0 for i in idx):
            drop_at = {-i for i in idx if i < 0}
            sub_names = [n for i, n in enumerate(rn, start=1) if i not in drop_at]
        else:
            sub_names = [rn[i - 1] for i in idx]
    else:
        sub_names = None
    cn = _col_names(mat)
    if drop and (sub.shape[0] == 1 or sub.shape[1] == 1):
        flat = np.array(sub, dtype=float).ravel(order="F")
        out = _RMatrix(flat, rownames=sub_names if sub.shape[1] == 1 else cn)
        return out
    return _RMatrix(sub, rownames=sub_names, colnames=cn)


def _m2i(obj):
    if _fun("is_chol")(obj.scale):
        return _fun("solve")(obj.scale, obj.mean)
    return _fun("Mult")(obj.scale, obj.mean)


def _i2m(obj):
    if _fun("is_chol")(obj.scale):
        return _fun("Mult")(obj.scale, obj.invcholmean)
    return _fun("solve")(obj.scale, obj.invcholmean)


def _copy_mv(obj: Mvnorm) -> Mvnorm:
    mean = None if obj.mean is None else np.array(obj.mean, dtype=float, copy=True)
    inv = None if obj.invcholmean is None else np.array(obj.invcholmean, dtype=float, copy=True)
    if mean is not None:
        mean = _RMatrix(mean, rownames=_row_names(obj.mean), colnames=_col_names(obj.mean))
    if inv is not None:
        inv = _RMatrix(inv, rownames=_row_names(obj.invcholmean), colnames=_col_names(obj.invcholmean))
    return Mvnorm(obj.scale, mean, inv)


def _attach_location(value, J, n_col, rcnames, matnames):
    """Validate ``mean`` or ``invcholmean`` and return a named matrix."""
    if not np.issubdtype(np.asarray(value).dtype, np.number):
        _stop("is.numeric(mean) is not TRUE")
    if _nrow(value) != J:
        _stop("NROW(mean) == dim(scale)[2L] is not TRUE")
    rn = _row_names(value)
    cn = _col_names(value)
    if not _is_matrix(value):
        value = r_matrix(value, nrow=_nrow(value))
        if rn is not None and len(rn) == value.shape[0]:
            pass
        else:
            rn = _row_names(value)
    else:
        value = np.array(value, dtype=float, copy=True)
    if rn is None:
        rn = list(rcnames) if rcnames is not None else None
    if rcnames is None:
        if rn is not None:
            _stop("rownames of mean do not match")
    elif list(rn) != list(rcnames):
        _stop("rownames of mean do not match")
    if matnames is not None and J == value.shape[1]:
        if cn is None:
            cn = list(matnames)
        if list(cn) != list(matnames):
            _stop("colnames of mean do not match")
    return _RMatrix(value, rownames=rn, colnames=cn)


def mvnorm(mean=MISSING, invcholmean=MISSING, chol=MISSING, invchol=MISSING):
    """Build an ``mvnorm`` model. R ``mvnorm``."""
    if chol is MISSING and invchol is MISSING:
        chol = _fun("as_chol")(_fun("ltMatrices")(1, diag=True))
    if (chol is MISSING) == (invchol is MISSING):
        _stop("xor(missing(chol), missing(invchol)) is not TRUE")
    if chol is not MISSING:
        if not _is_lt(chol):
            chol = _fun("as_ltMatrices")(chol)
        scale = _fun("as_chol")(chol)
    else:
        if not _is_lt(invchol):
            invchol = _fun("as_ltMatrices")(invchol)
        scale = _fun("as_invchol")(invchol)
    ret = Mvnorm(scale)
    J = _dim(scale)[1]
    rcnames = _rcnames(scale)
    matnames = _matnames(scale)
    if invcholmean is not MISSING:
        if mean is not MISSING:
            _stop("missing(mean) is not TRUE")
        ret.invcholmean = _attach_location(invcholmean, J, _ncol(invcholmean), rcnames, matnames)
    elif mean is not MISSING:
        ret.mean = _attach_location(mean, J, _ncol(mean), rcnames, matnames)
    return ret


def names_mvnorm(x: Mvnorm):
    """Variable names. R ``names.mvnorm``."""
    return _rcnames(x.scale)


def aperm_mvnorm(a: Mvnorm, perm, **kwargs):
    """Permute variables. R ``aperm.mvnorm``."""
    obj = _copy_mv(a)
    if obj.invcholmean is not None:
        obj.mean = _i2m(obj)
    ret = Mvnorm(_fun("aperm")(obj.scale, perm=perm, **kwargs))
    if obj.mean is not None:
        ret.mean = _rows(obj.mean, perm, drop=False)
    if a.invcholmean is not None:
        ret.invcholmean = _m2i(ret)
        ret.mean = None
    return ret


def simulate_mvnorm(
    object: Mvnorm,
    nsim=None,
    seed=None,
    standardize=False,
    as_data_frame=False,
    **kwargs,
):
    """Draw from the model. R ``simulate.mvnorm``.

    ``as_data_frame=True`` returns a dict of columns, one per variable,
    which is the shape of ``as.data.frame(t(ret))``.
    """
    N = _dim(object.scale)[0]
    J = _dim(object.scale)[1]
    if nsim is None:
        nsim = N
    nsim = int(nsim)
    if N > 1 and nsim != N:
        _stop("nsim == N is not TRUE")
    obj = _copy_mv(object)
    if standardize:
        if _fun("is_chol")(obj.scale):
            obj.scale = _standardize(chol=obj.scale)
        else:
            obj.scale = _standardize(invchol=obj.scale)
    with _seed_guard(seed):
        draws = np.array([norm_rand() for _ in range(nsim * J)], dtype=float)
    Z = draws.reshape((J, nsim), order="F")
    if obj.invcholmean is not None:
        Z = r_add(Z, obj.invcholmean)
    if _fun("is_chol")(obj.scale):
        Y = np.asarray(_fun("Mult")(obj.scale, Z), dtype=float)
    else:
        Y = np.asarray(_fun("solve")(obj.scale, Z), dtype=float)
    ret = Y
    if obj.mean is not None:
        ret = r_add(ret, obj.mean)
    rn = _rcnames(obj.scale)
    out = _RMatrix(ret, rownames=rn)
    if not as_data_frame:
        return out
    transposed = np.array(out, dtype=float).T
    names = list(rn) if rn is not None else [f"V{i + 1}" for i in range(J)]
    return {name: transposed[:, i].copy() for i, name in enumerate(names)}


def margDist(object: Mvnorm, which, **kwargs):
    """Marginal distribution. R ``margDist.mvnorm``."""
    if _fun("is_chol")(object.scale):
        part = _fun("marg_mvnorm")(chol=object.scale, which=which)
        scale = _fun("as_chol")(part["chol"])
    else:
        part = _fun("marg_mvnorm")(invchol=object.scale, which=which)
        scale = _fun("as_invchol")(part["invchol"])
    ret = Mvnorm(scale)
    mean = _i2m(object) if object.invcholmean is not None else object.mean
    if mean is not None:
        idx = _positions(which, _rcnames(object.scale), _dim(object.scale)[1])
        ret.mean = _rows(mean, idx, drop=False)
    if object.invcholmean is not None:
        ret.invcholmean = _m2i(ret)
        ret.mean = None
    return ret


def condDist(object: Mvnorm, which_given=1, given=MISSING, **kwargs):
    """Conditional distribution. R ``condDist.mvnorm``."""
    if given is MISSING:
        _stop('argument "given" is missing, with no default')
    obj = _copy_mv(object)
    had_inv = object.invcholmean is not None
    if had_inv:
        obj.mean = _i2m(obj)
    given_m = np.asarray(given, dtype=float)
    if given_m.ndim == 1:
        given_m = r_matrix(given_m, ncol=1)
    if obj.mean is not None:
        idx = _positions(which_given, _rcnames(obj.scale), _dim(obj.scale)[1])
        if obj.mean.shape[1] == 1 and given_m.shape[1] > 1:
            given_m = r_sub(given_m, _rows(obj.mean, idx, drop=True))
        else:
            center = _rows(obj.mean, idx, drop=False)
            given_m = np.asarray(given, dtype=float).ravel(order="F")
            given_m = r_sub(given_m, center)
            given_m = np.asarray(given_m, dtype=float).reshape(center.shape, order="F")
    if _fun("is_chol")(obj.scale):
        part = _fun("cond_mvnorm")(
            chol=obj.scale, which_given=which_given, given=given_m, **kwargs
        )
        scale = _fun("as_chol")(part["chol"])
    else:
        part = _fun("cond_mvnorm")(
            invchol=obj.scale, which_given=which_given, given=given_m, **kwargs
        )
        scale = _fun("as_invchol")(part["invchol"])
    ret = Mvnorm(scale)
    if "mean" in part and part["mean"] is not None:
        ret.mean = np.asarray(part["mean"], dtype=float)
    if obj.mean is not None:
        if isinstance(which_given, str) or (
            isinstance(which_given, (list, tuple)) and which_given and isinstance(which_given[0], str)
        ):
            which_num = _positions(which_given, _rcnames(object.scale), _dim(object.scale)[1])
        else:
            which_num = which_given
        rest = _rows(obj.mean, [-int(i) for i in np.atleast_1d(which_num)], drop=False)
        cond_mean = np.asarray(ret.mean if ret.mean is not None else 0.0, dtype=float)
        if obj.mean.shape[1] > 1 and np.ndim(cond_mean) == 2 and cond_mean.shape[1] > 1:
            ret.mean = _RMatrix(np.asarray(rest, dtype=float) + cond_mean)
        elif obj.mean.shape[1] == 1 and np.ndim(cond_mean) == 2 and cond_mean.shape[1] > 1:
            rest_v = _rows(obj.mean, [-int(i) for i in np.atleast_1d(which_num)], drop=True)
            ret.mean = _RMatrix(r_add(cond_mean, rest_v))
        else:
            ret.mean = _RMatrix(r_add(np.asarray(rest, dtype=float), np.asarray(cond_mean).ravel(order="F")))
    if had_inv:
        ret.invcholmean = _m2i(ret)
        ret.mean = None
    return ret


def _data_names(obs, lower, upper):
    """Shared name bookkeeping of ``logLik.mvnorm`` and ``lLgrad.mvnorm``."""
    nmiss = (obs is MISSING) + (lower is MISSING) + (upper is MISSING)
    if nmiss >= 3:
        _stop("nargs < 3L is not TRUE")
    nmobs = None
    if obs is not MISSING and obs is not None:
        if not _is_matrix(obs):
            _stop("is.matrix(obs) is not TRUE")
        nmobs = _row_names(obs)
        if nmobs is None:
            _stop("!is.null(rownames(obs)) is not TRUE")
    nmlower = nmupper = nmlu = None
    if lower is not MISSING and lower is not None:
        if not _is_matrix(lower):
            _stop("is.matrix(lower) is not TRUE")
        nmlower = _row_names(lower)
        if nmlower is None:
            _stop("!is.null(rownames(lower)) is not TRUE")
        nmlu = nmlower
    if upper is not MISSING:
        # R evaluates `lower` here, so a missing lower is an error.
        if lower is MISSING:
            _stop('argument "lower" is missing, with no default')
        if lower is not None:
            if upper is None:
                pass
            else:
                if not _is_matrix(upper):
                    _stop("is.matrix(upper) is not TRUE")
                nmupper = _row_names(upper)
                if nmupper is None:
                    _stop("!is.null(rownames(upper)) is not TRUE")
                if lower is not MISSING:
                    if nmlower != nmupper:
                        _stop("isTRUE(all.equal(nmlower, nmupper)) is not TRUE")
                else:
                    nmlu = nmupper
    nm = list(nmobs or []) + list(nmlu or [])
    return nmobs, nmlu, nm


def _perm_of(nm, no):
    if list(nm) == list(no):
        return None
    return list(nm) + [n for n in no if n not in nm]


def logLik_mvnorm(
    object: Mvnorm,
    obs=MISSING,
    lower=MISSING,
    upper=MISSING,
    standardize=False,
    **kwargs,
):
    """Log-likelihood of an ``mvnorm`` model. R ``logLik.mvnorm``."""
    object = _copy_mv(object)
    nmobs, nmlu, nm = _data_names(obs, lower, upper)
    no = list(names_mvnorm(object) or [])
    if not all(n in no for n in nm):
        _stop("all(nm %in% no) is not TRUE")
    perm = _perm_of(nm, no)
    args = {"scale": object.scale}
    if object.invcholmean is not None:
        args["invcholmean"] = object.invcholmean
    elif object.mean is not None:
        args["mean"] = object.mean
    args.update(kwargs)
    if obs is not MISSING:
        args["obs"] = obs
    if lower is not MISSING:
        args["lower"] = lower
    if upper is not MISSING:
        args["upper"] = upper
    if _fun("is_chol")(object.scale):
        args["chol"] = args.pop("scale")
        if standardize:
            args["chol"] = _standardize(chol=args["chol"])
            object.scale = args["chol"]
    else:
        args["invchol"] = args.pop("scale")
        if standardize:
            args["invchol"] = _standardize(invchol=args["invchol"])
            object.scale = args["invchol"]
    if perm is not None:
        ll = args["logLik"] if "logLik" in args and args["logLik"] is not None else True
        ret = 0.0
        if len(nm) < len(no) and nmlu is not None:
            object = margDist(object, which=nm)
        if nmobs is not None:
            ret = ret + logLik_mvnorm(margDist(object, which=nmobs), obs=obs, logLik=ll)
            if nmlu is not None:
                object = condDist(object, which_given=nmobs, given=obs)
        if nmlu is not None:
            ret = ret + logLik_mvnorm(object, lower=lower, upper=upper, **kwargs)
        return ret
    mixed = (
        args.get("invcholmean") is not None
        and (obs is not MISSING) + ((lower is not MISSING) or (upper is not MISSING)) == 2
    )
    if mixed:
        args["mean"] = _i2m(object)
        args.pop("invcholmean", None)
    return ldpmvnorm(**{k: v for k, v in args.items() if v is not MISSING})


def _lt_mask_index(J, diag):
    mask = np.asarray(_fun("lt")(J, diag=diag), dtype=bool)
    M = np.arange(1, J * J + 1).reshape((J, J), order="F")
    return M.ravel(order="F")[mask.ravel(order="F")].astype(int)


def _pad_score(score, extra_rows, byrow_orig, diag, names):
    cur = _fun("ltMatrices")(score, byrow=True)
    stacked = np.vstack([_unclass(cur), np.asarray(extra_rows, dtype=float)])
    out = _fun("ltMatrices")(stacked, byrow=True, diag=True, names=names)
    return _fun("ltMatrices")(out, byrow=byrow_orig)


def lLgrad(
    object: Mvnorm,
    obs=MISSING,
    lower=MISSING,
    upper=MISSING,
    standardize=False,
    **kwargs,
):
    """Score of an ``mvnorm`` log-likelihood. R ``lLgrad.mvnorm``.

    Marginalising a Cholesky factor (``om > 0`` on the chol path) reads
    ``args$invchol`` after that argument was removed. R 1.4-2 errors there;
    this port raises the same failure instead of inventing a value.
    """
    object = _copy_mv(object)
    original = object
    nmobs, nmlu, nm = _data_names(obs, lower, upper)
    no = list(names_mvnorm(object) or [])
    if not all(n in no for n in nm):
        _stop("all(nm %in% no) is not TRUE")
    perm = _perm_of(nm, no)
    args = {"scale": object.scale}
    if object.invcholmean is not None:
        args["invcholmean"] = object.invcholmean
    elif object.mean is not None:
        args["mean"] = object.mean
    args.update(kwargs)
    if obs is not MISSING:
        args["obs"] = obs
    if lower is not MISSING:
        args["lower"] = lower
    if upper is not MISSING:
        args["upper"] = upper
    need_mean = perm is not None or (
        args.get("invcholmean") is not None
        and (obs is not MISSING) + ((lower is not MISSING) or (upper is not MISSING)) == 2
    )
    if args.get("invcholmean") is not None and need_mean:
        args["mean"] = _i2m(object)
        args.pop("invcholmean", None)
    if _fun("is_chol")(object.scale):
        args["chol"] = args.pop("scale")
        sc = args["chol"]
        if standardize:
            sc = _standardize(chol=args["chol"])
            args["chol"] = sc
        pc = None
        if perm is not None:
            if not _diag(args["chol"]):
                args["chol"] = _fun("set_diagonals")(args["chol"], 1)
                sc = args["chol"]
            pc = _fun("aperm")(_fun("as_chol")(args["chol"]), perm=perm)
            args["chol"] = pc
            if len(nm) < len(no):
                args["chol"] = _fun("marg_mvnorm")(chol=args["chol"], which=nm)["chol"]
            if args.get("mean") is None:
                _stop("incorrect number of dimensions")
            args["mean"] = _rows(args["mean"], _positions(nm, no, len(no)), drop=False)
        ret = sldpmvnorm(**{k: v for k, v in args.items() if v is not MISSING})
        if ret.get("mean") is None:
            ret["mean"] = -np.asarray(ret["obs"], dtype=float)
        om = len(no) - len(nm)
        if om > 0:
            # R 1.4-2: this block indexes args$invchol on the chol path.
            if "invchol" not in args:
                _stop("subscript out of bounds")
            am = np.zeros((om, np.asarray(ret["mean"]).shape[1]))
            ret["mean"] = np.vstack([np.asarray(ret["mean"], dtype=float), am])
            Jo = _dim(original.scale)[1]
            pJ = _dim(args["invchol"])[1]
            nscore = _dim(ret["invchol"])[0]
            pad = np.zeros((Jo * (Jo + 1) // 2 - pJ * (pJ + 1) // 2, nscore))
            ret["chol"] = _pad_score(ret["chol"], pad, _byrow(ret["chol"]), True, perm)
        if perm is not None:
            ret["chol"] = deperma(
                chol=sc,
                permuted_chol=pc,
                perm=[no.index(p) + 1 for p in perm],
                score_schol=ret["chol"],
            )
        if standardize:
            ret["chol"] = destandardize(chol=original.scale, score_schol=ret["chol"])
        if not _diag(sc):
            ret["chol"] = _fun("ltMatrices")(
                _fun("Lower_tri")(ret["chol"], diag=False),
                diag=False,
                byrow=_byrow(ret["chol"]),
                names=_rcnames(ret["chol"]),
            )
        ret["scale"] = ret["chol"]
        ret.pop("chol", None)
        if ret.get("mean") is not None:
            order = _positions(no, _row_names(ret["mean"]) or no, len(no))
            ret["mean"] = _rows(ret["mean"], order, drop=False)
        if original.invcholmean is not None and ret.get("invcholmean") is None:
            J = _dim(sc)[1]
            idx = _lt_mask_index(J, True)
            X = np.asarray(ret["mean"], dtype=float)
            Y = r_matrix(original.invcholmean, nrow=X.shape[0], ncol=X.shape[1])
            n = X.shape[0]
            A = X[np.tile(np.arange(n), n), :] * Y[np.repeat(np.arange(n), n), :]
            scC = _fun("ltMatrices")(A[idx - 1, :], diag=True, byrow=False)
            if not _diag(sc):
                scC = _fun("ltMatrices")(
                    _fun("Lower_tri")(scC, diag=False), diag=False, byrow=False
                )
            scC = _fun("ltMatrices")(scC, byrow=_byrow(sc))
            ret["scale"] = _fun("ltMatrices")(
                _unclass(scC) + _unclass(ret["scale"]),
                diag=_diag(sc),
                byrow=_byrow(sc),
                names=_rcnames(sc),
            )
            ret["invcholmean"] = _fun("Mult")(sc, X, transpose=True)
            ret["mean"] = None
        return ret
    args["invchol"] = args.pop("scale")
    si = args["invchol"]
    if standardize:
        si = _standardize(invchol=args["invchol"])
        args["invchol"] = si
    pi = None
    if perm is not None:
        if not _diag(args["invchol"]):
            args["invchol"] = _fun("set_diagonals")(args["invchol"], 1)
            si = args["invchol"]
        pi = _fun("aperm")(_fun("as_invchol")(args["invchol"]), perm=perm)
        args["invchol"] = pi
        if len(nm) < len(no):
            args["invchol"] = _fun("marg_mvnorm")(invchol=args["invchol"], which=nm)["invchol"]
        if args.get("mean") is None:
            _stop("incorrect number of dimensions")
        args["mean"] = _rows(args["mean"], _positions(nm, no, len(no)), drop=False)
    ret = sldpmvnorm(**{k: v for k, v in args.items() if v is not MISSING})
    if ret.get("mean") is None and args.get("mean") is not None:
        ret["mean"] = -np.asarray(ret["obs"], dtype=float)
    om = len(no) - len(nm)
    if om > 0:
        am = np.zeros((om, np.asarray(ret["mean"]).shape[1]))
        ret["mean"] = np.vstack([np.asarray(ret["mean"], dtype=float), am])
        Jo = _dim(original.scale)[1]
        pJ = _dim(args["invchol"])[1]
        nscore = _dim(ret["invchol"])[0]
        pad = np.zeros((Jo * (Jo + 1) // 2 - pJ * (pJ + 1) // 2, nscore))
        ret["invchol"] = _pad_score(ret["invchol"], pad, _byrow(ret["invchol"]), True, perm)
    if perm is not None:
        ret["invchol"] = deperma(
            invchol=si,
            permuted_invchol=pi,
            perm=[no.index(p) + 1 for p in perm],
            score_schol=-_unclass(_fun("vectrick")(pi, ret["invchol"])),
        )
    if standardize:
        ret["invchol"] = destandardize(
            invchol=original.scale,
            score_schol=-_unclass(_fun("vectrick")(si, ret["invchol"])),
        )
    if not _diag(si):
        ret["invchol"] = _fun("ltMatrices")(
            _fun("Lower_tri")(ret["invchol"], diag=False),
            diag=False,
            byrow=_byrow(ret["invchol"]),
            names=_rcnames(ret["invchol"]),
        )
    ret["scale"] = ret["invchol"]
    ret.pop("invchol", None)
    if ret.get("mean") is not None:
        order = _positions(no, _row_names(ret["mean"]) or no, len(no))
        ret["mean"] = _rows(ret["mean"], order, drop=False)
    if original.invcholmean is not None and ret.get("invcholmean") is None:
        J = _dim(si)[1]
        idx = _lt_mask_index(J, True)
        X = np.asarray(ret["mean"], dtype=float)
        Y = r_matrix(original.invcholmean, nrow=X.shape[0], ncol=X.shape[1])
        n = X.shape[0]
        A = X[np.tile(np.arange(n), n), :] * Y[np.repeat(np.arange(n), n), :]
        scL = -np.asarray(_fun("vectrick")(_fun("solve")(si), A), dtype=float)
        scL = _fun("ltMatrices")(scL[idx - 1, :], diag=True, byrow=False)
        if not _diag(si):
            scL = _fun("ltMatrices")(_fun("Lower_tri")(scL, diag=False), diag=False, byrow=False)
        scL = _fun("ltMatrices")(scL, byrow=_byrow(si))
        ret["scale"] = _fun("ltMatrices")(
            _unclass(scL) + _unclass(ret["scale"]),
            diag=_diag(si),
            byrow=_byrow(si),
            names=_rcnames(si),
        )
        ret["invcholmean"] = _fun("solve")(si, X, transpose=True)
        ret["mean"] = False
    return ret


def mean_mvnorm(x: Mvnorm, **kwargs):
    """Marginal mean. R ``mean.mvnorm``."""
    if x.mean is not None:
        return x.mean
    if x.invcholmean is not None:
        return _i2m(x)
    return 0.0


def vcov_mvnorm(object: Mvnorm, **kwargs):
    """Covariance. R ``vcov.mvnorm``."""
    if _fun("is_invchol")(object.scale):
        return _fun("invchol2cov")(object.scale)
    return _fun("chol2cov")(object.scale)


def coef_mvnorm(object: Mvnorm, which=None, **kwargs):
    """Regression coefficients of one margin. R ``coef.mvnorm``.

    Returns ``None`` when the model has no mean, matching R's ``NULL``.
    The residual scale is the ``sigma`` attribute.
    """
    object = _copy_mv(object)
    J = _dim(object.scale)[1]
    if which is None:
        which = J
    if J == 1:
        if not _fun("is_invchol")(object.scale):
            object.scale = _fun("chol2invchol")(object.scale)
        if object.invcholmean is not None:
            object.mean = mean_mvnorm(object)
        if object.mean is None:
            return None
        sigma = 1.0 / _unclass(object.scale).ravel(order="F")
        return Coef(np.asarray(object.mean, dtype=float), sigma=sigma, rownames=_row_names(object.mean))
    if isinstance(which, str):
        rc = _rcnames(object.scale) or []
        which = [i + 1 for i, name in enumerate(rc) if name == which]
        if len(which) != 1:
            _stop("(length(which) == 1L) && (which > 1) is not TRUE")
        which = which[0]
    which = int(which)
    if not (which > 1 and which <= J):
        _stop("(length(which) == 1L) && (which > 1) && (which <= J) is not TRUE")
    if not _fun("is_invchol")(object.scale):
        object.scale = _fun("chol2invchol")(object.scale)
    diag = _diag(object.scale)
    packed = _fun("Lower_tri")(
        _fun("ltMatrices")(object.scale, byrow=True, diag=diag), diag=diag
    )
    packed = np.asarray(packed, dtype=float)
    if packed.ndim == 1:
        packed = packed.reshape((-1, 1))
    j = which - 1
    start = j * (j + 1) // 2
    idx = np.arange(start, start + which)
    ret = packed[idx, :]
    dg = ret[-1, :]
    cf = -ret[:-1, :]
    if object.mean is not None:
        object.invcholmean = _m2i(object)
    rn = list((_rcnames(object.scale) or [])[: which - 1])
    if object.invcholmean is not None:
        intercept = np.asarray(object.invcholmean, dtype=float)[which - 1, :]
        cf = np.vstack([intercept, cf])
        rn = ["(Intercept)"] + rn
    cf = cf / np.asarray(dg, dtype=float).reshape((1, -1))
    sigma = 1.0 / np.asarray(dg, dtype=float)
    if cf.shape[0] == 1 or cf.shape[1] == 1:
        flat = np.array(cf, dtype=float).ravel(order="F")
        return Coef(flat, sigma=sigma, rownames=rn)
    return Coef(cf, sigma=sigma, rownames=rn, colnames=_matnames(object.scale))


logLik = logLik_mvnorm
simulate = simulate_mvnorm
mean = mean_mvnorm
vcov = vcov_mvnorm
coef = coef_mvnorm
aperm = aperm_mvnorm
names = names_mvnorm
