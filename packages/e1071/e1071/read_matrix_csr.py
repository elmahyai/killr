"""Read a sparse matrix in CSR text format (e1071::read.matrix.csr)."""

from __future__ import annotations

import re
from typing import Any

from .write_matrix_csr import MatrixCsr

_WHITESPACE = re.compile(r" +")


def _split_line(line: str) -> list[str]:
    stripped = line.rstrip("\n\r")
    if not stripped:
        return []
    return [part for part in _WHITESPACE.split(stripped) if part]


def _line_has_y_label(first_token: str) -> bool:
    if first_token == "NA":
        return False
    return ":" not in first_token


def _parse_pairs(tokens: list[str]) -> list[tuple[int, float]]:
    pairs: list[tuple[int, float]] = []
    for token in tokens:
        column_text, value_text = token.split(":", 1)
        pairs.append((int(column_text), float(value_text)))
    return pairs


def _csr_to_dense(csr: MatrixCsr) -> list[float]:
    nrow, ncol = csr.dimension
    mat = [[0.0] * ncol for _ in range(nrow)]
    ra_len = len(csr.ra)
    for row in range(nrow):
        ia_start = csr.ia[row]
        ia_end = csr.ia[row + 1]
        if ia_start <= ra_len and ia_start < ia_end:
            for index in range(ia_start - 1, ia_end - 1):
                col = csr.ja[index] - 1
                if 0 <= col < ncol:
                    mat[row][col] = csr.ra[index]
    flat: list[float] = []
    for col in range(ncol):
        for row in range(nrow):
            flat.append(mat[row][col])
    return flat


def read_matrix_csr(
    file: str,
    fac: bool = True,
    ncol: int | None = None,
) -> MatrixCsr | dict[str, Any]:
    """Read a CSR text file and return a ``MatrixCsr`` or ``{x, y}``."""
    with open(file, encoding="utf-8") as handle:
        raw_lines = handle.readlines()

    line_tokens = [_split_line(line) for line in raw_lines]
    line_tokens = [tokens for tokens in line_tokens if tokens]
    if not line_tokens:
        dimension = (0, int(ncol) if ncol is not None else 0)
        empty = MatrixCsr([], [], [1], dimension)
        return empty

    y_labels: list[str] | None = None
    if _line_has_y_label(line_tokens[0][0]):
        y_labels = [tokens[0] for tokens in line_tokens]

    ja: list[int] = []
    ra: list[float] = []
    row_nnz: list[int] = []
    for index, tokens in enumerate(line_tokens):
        entry_tokens = tokens[1:] if y_labels is not None else tokens
        row_nnz.append(len(entry_tokens))
        for column, value in _parse_pairs(entry_tokens):
            ja.append(column)
            ra.append(value)

    ia = [1]
    running = 1
    for count in row_nnz:
        running += count
        ia.append(running)

    max_ja = max(ja) if ja else 0
    if ncol is None:
        ncol_out = max_ja
    else:
        ncol_out = max(int(ncol), max_ja)
    nrow = len(line_tokens)
    csr = MatrixCsr(ra, ja, ia, (nrow, ncol_out))

    if y_labels:
        if fac:
            y_out: Any = list(y_labels)
        else:
            y_out = [float(label) for label in y_labels]
        return {"x": csr, "y": y_out}
    return csr


def matrix_csr_as_numeric(csr: MatrixCsr) -> list[float]:
    """Column-major flatten like R ``as.numeric(as.matrix(matrix.csr))``."""
    return _csr_to_dense(csr)
