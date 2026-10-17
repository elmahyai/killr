"""Square-root factor of a positive-definite matrix (nlme ``pdFactor``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from nlme.pdmat import Dim, PdMat, is_initialized

try:
    import nlpdfactor
except ImportError:  # pragma: no cover - proof installs the crate
    nlpdfactor = None


@dataclass(slots=True)
class PdBlocked:
    """Block-diagonal ``pdBlocked`` object as a sequence of ``PdMat`` blocks."""

    blocks: tuple[PdMat, ...]
    names_list: tuple[tuple[str, ...], ...]
    dimnames: tuple[tuple[str, ...], tuple[str, ...]] | None = None
    pd_class: str = "pdBlocked"

    @property
    def classes(self) -> tuple[str, ...]:
        return (self.pd_class, "pdMat")


def pdFactor(object: PdMat | PdBlocked | Any) -> np.ndarray:
    """Extract the square-root factor of a ``pdMat`` object."""
    if isinstance(object, PdBlocked):
        return _pd_factor_pd_blocked(object)
    if isinstance(object, PdMat):
        dispatch = {
            "pdDiag": _pd_factor_pd_diag,
            "pdIdent": _pd_factor_pd_ident,
            "pdSymm": _pd_factor_pd_symm,
            "pdLogChol": _pd_factor_pd_log_chol,
            "pdNatural": _pd_factor_pd_natural,
            "pdCompSymm": _pd_factor_pd_comp_symm,
        }
        if object.pd_class in dispatch:
            return dispatch[object.pd_class](object)
        return _pd_factor_pd_mat(object)
    raise TypeError(f"no applicable method for 'pdFactor' applied to object of type {type(object)!r}")


def fingerprint_pd_factor(object: PdMat | PdBlocked) -> np.ndarray:
    """Column-major flattening of ``pdFactor`` for proof scripts."""
    factor = pdFactor(object)
    return np.asarray(factor, dtype=np.float64).reshape(-1, order="F")


def _pd_factor_pd_diag(object: PdMat) -> np.ndarray:
    values = np.exp(np.asarray(object.values, dtype=np.float64).ravel())
    return np.diag(values)


def _pd_factor_pd_ident(object: PdMat) -> np.ndarray:
    if object.ncol is None:
        raise ValueError("cannot extract the matrix with uninitialized dimensions")
    scale = float(np.exp(np.asarray(object.values, dtype=np.float64).ravel()[0]))
    return scale * np.eye(object.ncol, dtype=np.float64)


def _pd_factor_pd_symm(object: PdMat) -> np.ndarray:
    ncol = _pd_symm_ncol(int(object.values.size))
    flat = _matrix_log_pd(np.asarray(object.values, dtype=np.float64).ravel(), ncol)
    return flat.reshape(ncol, ncol, order="F")


def _pd_factor_pd_log_chol(object: PdMat) -> np.ndarray:
    _require_nlpdfactor()
    ncol = _pd_symm_ncol(int(object.values.size))
    flat = np.asarray(
        nlpdfactor.log_chol_pd_py(
            np.asarray(object.values, dtype=np.float64).ravel().tolist(),
            ncol,
        ),
        dtype=np.float64,
    )
    return flat.reshape(ncol, ncol, order="F")


def _pd_factor_pd_natural(object: PdMat) -> np.ndarray:
    _require_nlpdfactor()
    ncol = _pd_symm_ncol(int(object.values.size))
    flat = np.asarray(
        nlpdfactor.natural_pd_py(
            np.asarray(object.values, dtype=np.float64).ravel().tolist(),
            ncol,
        ),
        dtype=np.float64,
    )
    return flat.reshape(ncol, ncol, order="F")


def _pd_factor_pd_comp_symm(object: PdMat) -> np.ndarray:
    _require_nlpdfactor()
    if object.ncol is None:
        raise ValueError("cannot extract the matrix with uninitialized dimensions")
    ncol = int(object.ncol)
    flat = np.asarray(
        nlpdfactor.comp_symm_pd_py(
            np.asarray(object.values, dtype=np.float64).ravel().tolist(),
            ncol,
        ),
        dtype=np.float64,
    )
    return flat.reshape(ncol, ncol, order="F")


def _pd_factor_pd_mat(object: PdMat) -> np.ndarray:
    matrix = _pd_matrix(object, factor=False)
    q, r = np.linalg.qr(matrix)
    del q
    return np.asarray(r, dtype=np.float64).reshape(-1, order="F")


def _pd_factor_pd_blocked(object: PdBlocked) -> np.ndarray:
    if not all(is_initialized(block) for block in object.blocks):
        raise ValueError("cannot access the matrix of uninitialized objects")
    if not object.names_list:
        raise ValueError("cannot access the matrix of object without names")
    names = [name for group in object.names_list for name in group]
    side = len(names)
    value = np.zeros((side, side), dtype=np.float64)
    index = {name: pos for pos, name in enumerate(names)}
    for block, block_names in zip(object.blocks, object.names_list, strict=True):
        aux = pdFactor(block)
        aux = np.asarray(aux, dtype=np.float64)
        if aux.ndim == 1:
            aux = aux.reshape(int(np.sqrt(aux.size)), int(np.sqrt(aux.size)), order="F")
        positions = [index[name] for name in block_names]
        for row, i in enumerate(positions):
            for col, j in enumerate(positions):
                value[i, j] = aux[row, col]
    return value


def _pd_matrix(object: PdMat, factor: bool) -> np.ndarray:
    if not is_initialized(object):
        raise ValueError("cannot access the matrix of uninitialized objects")
    if object.pd_class == "pdDiag":
        side = int(object.values.size)
        if factor:
            return np.diag(np.exp(np.asarray(object.values, dtype=np.float64).ravel()))
        return np.diag(np.exp(2.0 * np.asarray(object.values, dtype=np.float64).ravel()))
    if object.pd_class == "pdIdent":
        if object.ncol is None:
            raise ValueError("cannot extract the matrix with uninitialized dimensions")
        scale = float(np.exp(np.asarray(object.values, dtype=np.float64).ravel()[0]))
        if factor:
            return scale * np.eye(object.ncol, dtype=np.float64)
        return (scale * scale) * np.eye(object.ncol, dtype=np.float64)
    if factor:
        return pdFactor(object)
    if object.pd_class in ("pdSymm", "pdLogChol", "pdNatural"):
        factor_mat = pdFactor(object)
        return factor_mat @ factor_mat.T
    if object.pd_class == "pdCompSymm":
        return _pd_matrix_comp_symm(object, factor=False)
    raise ValueError(f"cannot extract pdMatrix for class {object.pd_class!r}")


def _pd_matrix_comp_symm(object: PdMat, factor: bool) -> np.ndarray:
    if object.ncol is None:
        raise ValueError("cannot extract the matrix with uninitialized dimensions")
    ncol = int(object.ncol)
    obj = np.asarray(object.values, dtype=np.float64).ravel()
    aux = float(np.exp(obj[1]))
    aux_vec = np.array([float(np.exp(2.0 * obj[0])), (aux - 1.0 / (ncol - 1.0)) / (aux + 1.0)])
    if factor:
        return pdFactor(object)
    value = np.full((ncol, ncol), aux_vec[1], dtype=np.float64)
    np.fill_diagonal(value, 1.0)
    return aux_vec[0] * value


def _matrix_log_pd(params: np.ndarray, q: int) -> np.ndarray:
    """Port of ``matrixLog_pd`` from ``src/pdMat.c`` (column-major layout)."""
    if q == 1:
        return np.array([np.exp(params[0])], dtype=np.float64)
    l = np.zeros(q * q, dtype=np.float64)
    src = 0
    for i in range(q):
        row = i * q
        take = i + 1
        l[row : row + take] = params[src : src + take]
        src += take
    for i in range(q - 1):
        # R's copy_mat(L + i*(q+1)+1, 1, L + i*(q+1)+q, q, 1, q-(i+1)): lower column i gets upper row i.
        for k in range(q - (i + 1)):
            l[(i + 1 + k) + i * q] = l[i + (i + 1 + k) * q]
    mat = l.reshape(q, q, order="F")
    sym = (mat + mat.T) / 2.0
    values, vectors = np.linalg.eigh(sym)
    # R: vectors[i*qq + j] *= values[i] scales eigenvector column i, so V diag(exp(values)).
    scaled = vectors * np.exp(values)[None, :]
    return scaled.T.reshape(-1, order="F")


def _pd_symm_ncol(length: int) -> int:
    return int(round((np.sqrt(8 * length + 1) - 1) / 2))


def _require_nlpdfactor() -> None:
    if nlpdfactor is None:
        raise ImportError("nlpdfactor extension is required for this pdMat class")
