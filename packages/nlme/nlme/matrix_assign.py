"""Assignment of the matrix in special matrix objects (nlme ``matrix<-``).

R stores ``pdMat`` objects as unconstrained parameters and ``matrix()``
returns those parameters.  The helpers below use the same parameterisation
as R's ``pdConstruct`` / ``pdMatrix`` for the classes ``pdSymm``,
``pdLogChol``, ``pdDiag``, ``pdIdent`` and ``pdCompSymm``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

import numpy as np

from nlme.pdmat import PdMat, is_initialized as pd_mat_is_initialized
from nlme.restruct import PdMatElement, ReStruct

PD_CLASSES = ("pdSymm", "pdLogChol", "pdDiag", "pdIdent", "pdCompSymm")


def _as_matrix_value(value: Any) -> np.ndarray:
    """Return ``value`` as a two-dimensional float matrix (R ``as.matrix``)."""
    array = np.atleast_2d(np.asarray(value, dtype=np.float64))
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError("'value' must be a square matrix")
    return (array + array.T) / 2.0


def pd_params_from_matrix(pd_class: str, value: Any) -> np.ndarray:
    """Unconstrained parameters of a positive-definite matrix for ``pd_class``."""
    mat = _as_matrix_value(value)
    n = mat.shape[0]
    if pd_class == "pdSymm":
        # R stores half the matrix logarithm: M = expm(2 * S) with S = logm(M) / 2.
        eigvals, eigvecs = np.linalg.eigh(mat)
        half_log_mat = 0.5 * (eigvecs * np.log(eigvals)) @ eigvecs.T
        return half_log_mat[np.triu_indices(n)].astype(np.float64)
    if pd_class == "pdLogChol":
        upper = np.linalg.cholesky(mat).T
        diag = np.log(np.diag(upper))
        return np.concatenate([diag, upper[np.triu_indices(n, k=1)]]).astype(np.float64)
    if pd_class == "pdDiag":
        return np.log(np.sqrt(np.diag(mat))).astype(np.float64)
    if pd_class == "pdIdent":
        return np.array([np.log(np.sqrt(np.mean(np.diag(mat))))], dtype=np.float64)
    if pd_class == "pdCompSymm":
        sd = np.sqrt(np.mean(np.diag(mat)))
        off = mat[np.triu_indices(n, k=1)]
        rho = float(np.mean(off)) / (sd * sd) if off.size else 0.0
        return np.array([np.log(sd), np.log((1.0 + rho) / (1.0 - rho))], dtype=np.float64)
    raise ValueError(f"unknown pd class {pd_class!r}")


def pd_matrix_from_params(pd_class: str, values: Any, ncol: int) -> np.ndarray:
    """Positive-definite matrix from unconstrained parameters (inverse of the above)."""
    params = np.asarray(values, dtype=np.float64).ravel()
    n = int(ncol)
    if pd_class == "pdSymm":
        sym = np.zeros((n, n), dtype=np.float64)
        sym[np.triu_indices(n)] = params
        sym = sym + sym.T - np.diag(np.diag(sym))
        eigvals, eigvecs = np.linalg.eigh(sym)
        return (eigvecs * np.exp(2.0 * eigvals)) @ eigvecs.T
    if pd_class == "pdLogChol":
        upper = np.zeros((n, n), dtype=np.float64)
        upper[np.diag_indices(n)] = np.exp(params[:n])
        upper[np.triu_indices(n, k=1)] = params[n:]
        return upper.T @ upper
    if pd_class == "pdDiag":
        return np.diag(np.exp(2.0 * params))
    if pd_class == "pdIdent":
        return float(np.exp(2.0 * params[0])) * np.eye(n)
    if pd_class == "pdCompSymm":
        sd = float(np.exp(params[0]))
        rho = float(np.tanh(params[1] / 2.0))
        return sd * sd * ((1.0 - rho) * np.eye(n) + rho * np.ones((n, n)))
    raise ValueError(f"unknown pd class {pd_class!r}")


def _dim_of(names: Sequence[str], ncol: int | None) -> int:
    if names:
        return len(names)
    if ncol is not None:
        return int(ncol)
    raise ValueError("cannot determine the dimension of an unnamed pdMat object")


def _assign_pd_mat(object: PdMat, value: Any) -> PdMat:
    mat = _as_matrix_value(value)
    if pd_mat_is_initialized(object):
        side = _dim_of(object.names, object.ncol)
        if mat.shape != (side, side):
            raise ValueError('cannot change dimensions on an initialized "pdMat" object')
    values = pd_params_from_matrix(object.pd_class, mat)
    ncol = mat.shape[0] if object.pd_class in ("pdIdent", "pdCompSymm") else object.ncol
    return replace(object, values=values, ncol=ncol)


def _assign_pd_mat_element(object: PdMatElement, value: Any) -> PdMatElement:
    mat = _as_matrix_value(value)
    side = len(object.names)
    if object.values.size > 0 and mat.shape != (side, side):
        raise ValueError('cannot change dimensions on an initialized "pdMat" object')
    if mat.shape[0] != side:
        raise ValueError("length of 'nam' not consistent with dimensions of initial value")
    return replace(object, values=pd_params_from_matrix(object.pd_class, mat))


def _assign_restruct(object: ReStruct, value: Any) -> ReStruct:
    if not isinstance(value, (list, tuple)):
        value = [value]
    if len(value) != len(object.blocks):
        raise ValueError("cannot change the length of 'object'")
    reversed_value = list(reversed(list(value)))  # same order as object
    blocks = [
        (name, _assign_pd_mat_element(element, reversed_value[index]))
        for index, (name, element) in enumerate(object.blocks)
    ]
    return ReStruct(blocks=blocks, settings=object.settings.copy(), plen=object.plen)


def matrix_assign(object: Any, value: Any):
    """Return ``object`` with its matrix replaced by ``value`` (R ``matrix<-``)."""
    if isinstance(object, ReStruct):
        return _assign_restruct(object, value)
    if isinstance(object, PdMat):
        return _assign_pd_mat(object, value)
    if isinstance(object, PdMatElement):
        return _assign_pd_mat_element(object, value)
    raise TypeError(f"no applicable method for 'matrix<-' applied to {type(object).__name__}")
