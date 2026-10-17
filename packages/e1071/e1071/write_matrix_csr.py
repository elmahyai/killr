"""Write a sparse matrix in CSR text format (e1071::write.matrix.csr)."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

_MACHINE_EPS = np.finfo(float).eps


class MatrixCsr:
    __slots__ = ("ra", "ja", "ia", "dimension")

    def __init__(
        self,
        ra: list[float],
        ja: list[int],
        ia: list[int],
        dimension: tuple[int, int],
    ) -> None:
        self.ra = ra
        self.ja = ja
        self.ia = ia
        self.dimension = dimension

    @property
    def nrow(self) -> int:
        return self.dimension[0]

    @property
    def ncol(self) -> int:
        return self.dimension[1]


def _is_matrix_csr(x: Any) -> bool:
    if isinstance(x, MatrixCsr):
        return True
    if isinstance(x, dict):
        return all(k in x for k in ("ra", "ja", "ia", "dimension"))
    return all(hasattr(x, name) for name in ("ra", "ja", "ia", "dimension"))


def _matrix_csr_from_obj(x: Any) -> MatrixCsr:
    if isinstance(x, MatrixCsr):
        return x
    ra = list(getattr(x, "ra", x["ra"]))
    ja = [int(v) for v in getattr(x, "ja", x["ja"])]
    ia = [int(v) for v in getattr(x, "ia", x["ia"])]
    dim = getattr(x, "dimension", x["dimension"])
    dimension = (int(dim[0]), int(dim[1]))
    return MatrixCsr([float(v) for v in ra], ja, ia, dimension)


def _as_dense_matrix(x: Any) -> np.ndarray:
    if isinstance(x, np.ndarray):
        if x.ndim != 2:
            raise ValueError("x must be a matrix")
        return np.asarray(x, dtype=float)
    if hasattr(x, "shape") and len(x.shape) == 2:
        return np.asarray(x, dtype=float)
    if isinstance(x, list):
        if not x:
            return np.zeros((0, 0), dtype=float)
        if isinstance(x[0], (list, tuple)):
            return np.asarray(x, dtype=float)
        nrow = 1
        ncol = len(x)
        return np.asarray(x, dtype=float).reshape(nrow, ncol)
    raise TypeError("x cannot be converted to a matrix")


def _as_matrix_csr(x: Any, *, eps: float = _MACHINE_EPS) -> MatrixCsr:
    if _is_matrix_csr(x):
        return _matrix_csr_from_obj(x)

    mat = _as_dense_matrix(x)
    nrow, ncol = mat.shape
    if nrow == 0 or ncol == 0:
        return MatrixCsr([], [], [1], (nrow, ncol))

    ra: list[float] = []
    ja: list[int] = []
    ia: list[int] = [1]
    for i in range(nrow):
        for j in range(ncol):
            value = float(mat[i, j])
            if abs(value) >= eps:
                ra.append(value)
                ja.append(j + 1)
        ia.append(len(ra) + 1)

    if not ra:
        ia = [1] + [2] * nrow
        return MatrixCsr([0.0], [1], ia, (nrow, ncol))

    return MatrixCsr(ra, ja, ia, (nrow, ncol))


def _format_csr_number(value: float) -> str:
    if value == 0.0 and math.copysign(1.0, value) < 0:
        return "-0"
    if value == int(value) and abs(value) < 2**53:
        return str(int(value))
    text = format(value, ".16g")
    if "e" in text or "E" in text:
        return text.replace("E", "e")
    return text


def write_matrix_csr(
    x: Any,
    file: str = "out.dat",
    y: Sequence[Any] | None = None,
    fac: bool = True,
) -> None:
    """Write ``x`` in CSR text format to ``file``."""
    csr = _as_matrix_csr(x)
    nrow, ncol = csr.dimension

    if y is not None and len(y) != nrow:
        raise ValueError(
            f"Length of y (={len(y)}) does not match number of rows of x (={nrow})!"
        )

    labels: list[str] | None = None
    if y is not None:
        labels = []
        for item in y:
            if isinstance(item, (int, float, np.number)) and not isinstance(item, bool):
                labels.append(_format_csr_number(float(item)))
            else:
                labels.append(str(item))

    ra_len = len(csr.ra)
    zerocols = bool(csr.ja) and all(j < ncol for j in csr.ja)

    with open(file, "w", encoding="utf-8") as handle:
        for i in range(nrow):
            if labels is not None:
                handle.write(labels[i])
                handle.write(" ")
            ia_i = csr.ia[i]
            ia_next = csr.ia[i + 1]
            if ia_i <= ra_len and ia_i < ia_next:
                for j in range(ia_i - 1, ia_next - 1):
                    handle.write(f"{csr.ja[j]}:{_format_csr_number(csr.ra[j])} ")
                if zerocols:
                    handle.write(f"{ncol}:0 ")
                    zerocols = False
            handle.write("\n")
