"""Recalculate a condensed linear object under a model plug-in (nlme ``recalc``)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

import numpy as np

from nlme.corident import CorIdent
from nlme.corarma import recalc_arma
from nlme.restruct import ReStruct, recalc_restruct
from nlme.conlin import ConLin
from nlme.var_ident import VarIdent
from nlme.var_power import VarPower
from nlme.varcomb import VarComb

try:
    import nlmerecalc
except ImportError:  # pragma: no cover - the extension is installed for proofs
    nlmerecalc = None

_KERNEL_NOTE = {
    "CorSymm": "symm_recalc",
    "CorNatural": "nat_recalc",
    "CorCompSymm": "comp_symm_recalc",
    "CorAR1": "ar1_recalc",
}

_BLOCKED_NOTE: dict[str, str] = {}

# ``spClass`` as ``Dim.corSpatial`` sets it: spherical, exponential, Gaussian, linear, rational.
_SPATIAL_CLASS = {"CorSpher": 1, "CorExp": 2, "CorGaus": 3, "CorLin": 4, "CorRatio": 5}


def recalc(object: Any, conLin: ConLin, **_ignored) -> ConLin:
    """Apply a model plug-in to ``conLin`` and return the updated linear object."""
    if isinstance(object, ReStruct):
        return recalc_restruct(object, conLin)
    if isinstance(object, (list, tuple)):
        return _recalc_model_struct(object, conLin)
    if _is_model_struct(object):
        return _recalc_model_struct(list(object.components.values()), conLin)
    if isinstance(object, CorIdent):
        return conLin
    if isinstance(object, VarIdent) and object.formula is None:
        return conLin
    if isinstance(object, (VarIdent, VarPower, VarComb)):
        return _recalc_var_func(object, conLin)
    # UseMethod: a recalc method the user defined on the class (or a user base class) comes first.
    user_recalc = _user_method(object, "recalc")
    if user_recalc is not None:
        return user_recalc(object, conLin)
    name = type(object).__name__
    if name in {"CorSymm", "CorNatural", "CorCompSymm", "CorAR1"}:
        return _recalc_correlation(object, conLin, name)
    if name == "CorARMA":
        return recalc_arma(object, conLin)
    if name in _SPATIAL_CLASS:
        return _recalc_spatial(object, conLin, name)
    if name == "CorCAR1":
        return _recalc_car1(object, conLin)
    # UseMethod falls through to recalc.corStruct for a user class that supplies corMatrix.
    if _user_method(object, "corMatrix") is not None:
        return recalc_cor_struct(object, conLin)
    blocked = _BLOCKED_NOTE.get(name)
    if blocked is not None:
        raise NotImplementedError(blocked)
    kernel = _KERNEL_NOTE.get(name)
    if kernel is not None:
        raise NotImplementedError(f"recalc for {name} needs the {kernel} kernel")
    raise NotImplementedError(f"recalc is not translated for {name}")


def _is_model_struct(object: Any) -> bool:
    """``glsStruct``, ``lmeStruct``, and similar lists hold named components."""
    components = getattr(object, "components", None)
    return isinstance(components, dict)


def _recalc_model_struct(components: Sequence[Any], conLin: ConLin) -> ConLin:
    """``recalc.modelStruct``: components are applied from last to first."""
    for component in reversed(list(components)):
        conLin = recalc(component, conLin)
    return conLin


def _recalc_var_func(object: VarIdent | VarComb, conLin: ConLin) -> ConLin:
    """``recalc.varFunc``: scale ``Xy`` by the weights and add the variance log-likelihood."""
    weights = _var_weights(object)
    log_lik = _var_log_lik(object)
    xy = np.asarray(conLin.Xy, dtype=np.float64)
    if xy.ndim == 1:
        xy = xy.reshape(-1, 1)
    scaled = xy * weights.reshape(-1, 1)
    return replace(conLin, Xy=scaled, logLik=float(conLin.logLik) + log_lik)


def _recalc_correlation(object: Any, conLin: ConLin, name: str) -> ConLin:
    """Run the native correlation recalc kernel for one initialized structure."""
    if nlmerecalc is None:
        raise ImportError("nlmerecalc extension is required for correlation recalc")
    dim = getattr(object, "dim", None)
    if dim is None or not hasattr(dim, "as_pdims"):
        raise ValueError(f"{name} object must be initialized before recalc")
    xy = np.asarray(conLin.Xy, dtype=np.float64)
    if xy.ndim == 1:
        n = int(dim.N)
        if n == 0 or xy.size % n:
            raise ValueError("ConLin.Xy has incompatible dimensions")
        xy = xy.reshape(n, xy.size // n, order="F")
    elif xy.ndim != 2:
        raise ValueError("ConLin.Xy must be a vector or matrix")
    n, zxcol = xy.shape
    if n != int(dim.N):
        raise ValueError("ConLin.Xy row count does not match correlation dimensions")
    flat = np.asarray(xy, dtype=np.float64, order="F").reshape(-1, order="F")
    pdims = np.asarray(dim.as_pdims(), dtype=np.int32).tolist()
    # R's recalc.<corStruct> passes logLik = double(1) to the kernel and adds the
    # result to conLin$logLik afterwards. Keep that order so the rounding matches.
    log_lik = 0.0
    if name == "CorSymm":
        covariate = getattr(object, "covariate", None)
        if isinstance(covariate, dict):
            time = np.concatenate(
                [np.asarray(values, dtype=np.int32).reshape(-1) for values in covariate.values()]
            )
        elif covariate is not None:
            time = np.asarray(covariate, dtype=np.int32).reshape(-1)
        else:
            raise ValueError("CorSymm object has no covariate")
        flat, log_lik = nlmerecalc.symm_recalc(
            flat.tolist(), pdims, zxcol, np.asarray(object.value).reshape(-1).tolist(),
            time.tolist(), int(object.max_cov), log_lik
        )
    elif name == "CorNatural":
        max_cov = getattr(object, "max_cov", None)
        covariate = getattr(object, "covariate", None)
        if max_cov is None or covariate is None:
            raise ValueError("CorNatural object must provide max_cov and covariate")
        if isinstance(covariate, dict):
            time = np.concatenate(
                [np.asarray(values, dtype=np.int32).reshape(-1) for values in covariate.values()]
            )
        else:
            time = np.asarray(covariate, dtype=np.int32).reshape(-1)
        flat, log_lik = nlmerecalc.nat_recalc(
            flat.tolist(), pdims, zxcol, np.asarray(object.value).reshape(-1).tolist(),
            time.tolist(), int(max_cov), log_lik
        )
    elif name == "CorCompSymm":
        if getattr(object, "inf", None) is None:
            raise ValueError("CorCompSymm object must be initialized before recalc")
        flat, _par, log_lik = nlmerecalc.comp_symm_recalc(
            flat.tolist(), pdims, zxcol, float(object.value), float(object.inf), log_lik
        )
    else:
        # R's recalc.corAR1 leaves the object unchanged; the kernel's transformed phi is not stored.
        flat, _par, log_lik = nlmerecalc.ar1_recalc(
            flat.tolist(), pdims, zxcol, float(object.value), log_lik
        )
    return replace(
        conLin,
        Xy=np.asarray(flat, dtype=np.float64).reshape((n, zxcol), order="F"),
        logLik=float(conLin.logLik) + float(log_lik),
    )


def _xy_matrix(conLin: ConLin, n: int) -> np.ndarray:
    """``Xy`` as an ``(n, ZXcol)`` array, reshaped column-major as R's ``as.double`` would see it."""
    xy = np.asarray(conLin.Xy, dtype=np.float64)
    if xy.ndim == 1:
        if n == 0 or xy.size % n:
            raise ValueError("ConLin.Xy has incompatible dimensions")
        xy = xy.reshape(n, xy.size // n, order="F")
    elif xy.ndim != 2:
        raise ValueError("ConLin.Xy must be a vector or matrix")
    if xy.shape[0] != n:
        raise ValueError("ConLin.Xy row count does not match correlation dimensions")
    return xy


def _group_vectors(covariate: Any) -> list[np.ndarray]:
    """Per-group covariate vectors in group order (R's ``unlist(getCovariate(object))``)."""
    if covariate is None:
        raise ValueError("object has no covariate; initialize it before recalc")
    if isinstance(covariate, dict):
        items = list(covariate.values())
    elif isinstance(covariate, (list, tuple)):
        items = list(covariate)
    else:
        items = [covariate]
    return [np.asarray(v, dtype=np.float64).reshape(-1) for v in items]


def _recalc_spatial(object: Any, conLin: ConLin, name: str) -> ConLin:
    """``recalc.corSpatial``: the spatial kernel on the stored (unconstrained) range and nugget."""
    if nlmerecalc is None or not hasattr(nlmerecalc, "spatial_recalc"):
        raise ImportError("nlmerecalc extension with spatial_recalc is required for spatial recalc")
    dim = getattr(object, "dim", None)
    if dim is None:
        raise ValueError(f"{name} object must be initialized before recalc")
    lens = [int(v) for v in dim.len]
    # Unlike Dim.corStruct, Dim.corSpatial starts each group at its cumulative pair count.
    starts: list[int] = []
    acc = 0
    for m in lens:
        starts.append(acc)
        acc += m * (m - 1) // 2
    pdims = [int(dim.N), int(dim.M), _SPATIAL_CLASS[name], int(dim.sum_len_sq)] + lens + starts
    xy = _xy_matrix(conLin, int(dim.N))
    n, zxcol = xy.shape
    flat = np.asarray(xy, dtype=np.float64, order="F").reshape(-1, order="F")
    dist = np.concatenate(_group_vectors(object.covariate))
    par = np.asarray(object.value, dtype=np.float64).reshape(-1).tolist()
    min_d = 0.0 if object.min_d is None else float(object.min_d)
    xy_out, _par, log_lik = nlmerecalc.spatial_recalc(
        flat.tolist(), pdims, zxcol, par, dist.tolist(), min_d, bool(object.nugget),
        _SPATIAL_CLASS[name], 0.0,
    )
    return replace(
        conLin,
        Xy=np.asarray(xy_out, dtype=np.float64).reshape((n, zxcol), order="F"),
        logLik=float(conLin.logLik) + float(log_lik),
    )


def _recalc_car1(object: Any, conLin: ConLin) -> ConLin:
    """``recalc.corCAR1``: the CAR(1) kernel on the stored logit parameter and the times."""
    if nlmerecalc is None or not hasattr(nlmerecalc, "car1_recalc"):
        raise ImportError("nlmerecalc extension with car1_recalc is required for CAR(1) recalc")
    dim = getattr(object, "dim", None)
    if dim is None:
        raise ValueError("CorCAR1 object must be initialized before recalc")
    xy = _xy_matrix(conLin, int(dim.N))
    n, zxcol = xy.shape
    flat = np.asarray(xy, dtype=np.float64, order="F").reshape(-1, order="F")
    time = np.concatenate(_group_vectors(object.covariate))
    xy_out, _phi, log_lik = nlmerecalc.car1_recalc(
        flat.tolist(), [int(v) for v in dim.as_pdims()], zxcol, float(object.value),
        time.tolist(), 0.0,
    )
    return replace(
        conLin,
        Xy=np.asarray(xy_out, dtype=np.float64).reshape((n, zxcol), order="F"),
        logLik=float(conLin.logLik) + float(log_lik),
    )


def _user_method(object: Any, name: str):
    """Method lookup as R's UseMethod: the MRO of the object, skipping nlme's own classes.

    A user class is one defined outside the ``nlme`` package. The first class in the MRO that
    defines ``name`` wins, the same order as the class vector R searches.
    """
    for cls in type(object).__mro__:
        if cls.__module__.split(".")[0] == "nlme":
            continue
        method = vars(cls).get(name)
        if callable(method):
            return method
    return None


def recalc_cor_struct(object: Any, conLin: ConLin) -> ConLin:
    """``recalc.corStruct``: the generic path for a correlation class that supplies ``corMatrix``.

    R: ``Xy[] <- corStruct_recalc(Xy, Dim(object), ZXcol, corFactor(object))`` and
    ``logLik <- logLik + logLik(object)``. A user ``recalc`` method calls this as ``NextMethod``.
    """
    dim = getattr(object, "dim", None)
    if dim is None:
        raise ValueError("corStruct object must be initialized before recalc")
    xy = _xy_matrix(conLin, int(dim.N))
    factor, log_lik = _cor_struct_factor(object, dim)
    out = np.array(xy, dtype=np.float64, copy=True)
    start = 0
    pos = 0
    # corStruct_recalc: each group's rows of Xy are multiplied on the left by its factor block.
    for length in dim.len:
        block = factor[pos : pos + length * length].reshape((length, length), order="F")
        out[start : start + length, :] = block @ xy[start : start + length, :]
        start += length
        pos += length * length
    return replace(conLin, Xy=out, logLik=float(conLin.logLik) + log_lik)


def _cor_struct_factor(object: Any, dim: Any) -> tuple[np.ndarray, float]:
    """``corFactor.corStruct`` through ``corStruct_factList``: inverse Cholesky factor per group.

    Returns the packed factor (column-major blocks) and the ``logDet`` attribute, which is the
    value ``logLik(object)`` adds. ``chol`` gives ``mat = L L'`` (R's upper factor is ``L'``); the
    factor is ``inv(L)``, the solution of ``L x = e_j`` in each column.
    """
    blocks = _corr_blocks(object)
    if len(blocks) != len(dim.len):
        raise ValueError("corMatrix returned a different number of groups than Dim")
    factor = np.zeros(int(dim.sum_len_sq), dtype=np.float64)
    log_det = 0.0
    pos = 0
    for mat, length in zip(blocks, dim.len):
        mat = np.asarray(mat, dtype=np.float64).reshape((length, length), order="F")
        lower = np.linalg.cholesky(mat)
        log_det -= float(np.sum(np.log(np.abs(np.diag(lower)))))
        inv = np.linalg.solve(lower, np.eye(length))
        factor[pos : pos + length * length] = inv.reshape(-1, order="F")
        pos += length * length
    return factor, log_det


def _corr_blocks(object: Any) -> list[np.ndarray]:
    """``corMatrix(object)`` with ``corr = TRUE`` as a list of group blocks."""
    method = _user_method(object, "corMatrix")
    if method is None:
        label = type(object).__name__
        raise ValueError(f'do not know how to calculate correlation matrix of "{label}" object')
    val = method(object, covariate=getattr(object, "covariate", None), corr=True)
    if isinstance(val, dict):
        return [np.asarray(v, dtype=np.float64) for v in val.values()]
    if isinstance(val, (list, tuple)):
        return [np.asarray(v, dtype=np.float64) for v in val]
    return [np.asarray(val, dtype=np.float64)]


def _var_weights(object: VarIdent | VarComb) -> np.ndarray:
    if isinstance(object, VarComb):
        weights = None
        for component in object.components:
            current = _var_weights(component)
            weights = current if weights is None else weights * current
        if weights is None:
            raise ValueError("varComb object has no components")
        return np.asarray(weights, dtype=np.float64)
    if object.weights is None:
        raise ValueError("varFunc object has no weights; initialize it before recalc")
    return np.asarray(object.weights, dtype=np.float64).reshape(-1)


def _var_log_lik(object: VarIdent | VarComb) -> float:
    if isinstance(object, VarComb):
        return float(sum(_var_log_lik(component) for component in object.components))
    if object.log_lik is None:
        raise ValueError("varFunc object has no logLik; initialize it before recalc")
    return float(object.log_lik)


def proof_values(conLin: ConLin) -> np.ndarray:
    """Column-major ``Xy`` followed by ``logLik`` for R comparison."""
    xy = np.asarray(conLin.Xy, dtype=np.float64).reshape(-1, order="F")
    return np.concatenate([xy, np.array([float(conLin.logLik)], dtype=np.float64)])
