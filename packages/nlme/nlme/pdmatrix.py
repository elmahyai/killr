"""Extract the positive-definite or square-root factor matrix (nlme ``pdMatrix``).

Methods translated here: ``pdMatrix.pdDiag``, ``pdMatrix.pdIdent``,
``pdMatrix.pdCompSymm``, ``pdMatrix.pdLogChol`` (through the ``nlpdfactor``
kernel), and ``pdMatrix.pdBlocked``. ``pdSymm`` delegates to the translated
``pdFactor``.
"""

from __future__ import annotations

import numpy as np

from nlme.pdmat import PdMat, is_initialized

try:
    import nlpdfactor
except ImportError:  # pragma: no cover - the proof installs the crate
    nlpdfactor = None


def pdMatrix(object, factor: bool = False) -> np.ndarray:
    """Return the ``pdMat`` matrix, or its square-root factor when ``factor`` is true."""
    from nlme.pdfactor import PdBlocked

    if isinstance(object, PdBlocked):
        return _pd_matrix_blocked(object, factor)
    if not isinstance(object, PdMat):
        raise TypeError(f"no applicable method for 'pdMatrix' applied to {type(object)!r}")
    if not is_initialized(object):
        raise ValueError("cannot access the matrix of uninitialized objects")

    cls = object.pd_class
    values = np.asarray(object.values, dtype=np.float64).ravel()
    if cls == "pdDiag":
        scale = np.exp(values) if factor else np.exp(2.0 * values)
        return np.diag(scale)
    if cls == "pdIdent":
        if object.ncol is None:
            raise ValueError("cannot extract the matrix with uninitialized dimensions")
        scale = float(np.exp(values[0])) if factor else float(np.exp(2.0 * values[0]))
        return scale * np.eye(object.ncol, dtype=np.float64)
    if cls == "pdCompSymm":
        return _pd_matrix_comp_symm(object, values, factor)
    if cls == "pdLogChol":
        factor_mat = _pd_factor_log_chol(values)
        return factor_mat if factor else factor_mat.T @ factor_mat
    if cls == "pdSymm":
        from nlme.pdfactor import pdFactor

        factor_mat = np.asarray(pdFactor(object), dtype=np.float64)
        return factor_mat if factor else factor_mat.T @ factor_mat
    raise NotImplementedError(f"pdMatrix for class {cls!r} is not translated")


def _pd_matrix_comp_symm(object: PdMat, values: np.ndarray, factor: bool) -> np.ndarray:
    if object.ncol is None:
        raise ValueError("cannot extract the matrix with uninitialized dimensions")
    ncol = int(object.ncol)
    aux1 = float(np.exp(2.0 * values[0]))
    exp_z = float(np.exp(values[1]))
    aux2 = (exp_z - 1.0 / (ncol - 1.0)) / (exp_z + 1.0)
    if factor:
        if nlpdfactor is None:
            raise ImportError("nlpdfactor extension is required for pdCompSymm factors")
        flat = np.asarray(nlpdfactor.comp_symm_pd_py(values.tolist(), ncol), dtype=np.float64)
        return flat.reshape(ncol, ncol, order="F")
    value = np.full((ncol, ncol), aux2, dtype=np.float64)
    np.fill_diagonal(value, 1.0)
    return aux1 * value


def _pd_factor_log_chol(values: np.ndarray) -> np.ndarray:
    if nlpdfactor is None:
        raise ImportError("nlpdfactor extension is required for pdLogChol factors")
    q = int(round((np.sqrt(8 * values.size + 1) - 1) / 2))
    flat = np.asarray(nlpdfactor.log_chol_pd_py(values.tolist(), q), dtype=np.float64)
    return flat.reshape(q, q, order="F")


def _pd_matrix_blocked(object, factor: bool) -> np.ndarray:
    if not all(is_initialized(block) for block in object.blocks):
        raise ValueError("cannot access the matrix of uninitialized objects")
    if not object.names_list:
        raise ValueError("cannot access the matrix of object without names")
    side = sum(len(names) for names in object.names_list)
    value = np.zeros((side, side), dtype=np.float64)
    offset = 0
    for block in object.blocks:
        aux = pdMatrix(block, factor)
        size = aux.shape[0]
        value[offset : offset + size, offset : offset + size] = aux
        offset += size
    return value
