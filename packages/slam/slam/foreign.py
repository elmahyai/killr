"""CLUTO and MC sparse-matrix readers and writers."""

import os
from pathlib import Path

import numpy as np

from slam._arrays import as_matrix, as_simple_triplet_matrix, simple_triplet_matrix, transpose


def _r_token(value):
    number = float(value)
    if np.isfinite(number) and number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    return format(number, ".15g")


def _na_omit(values):
    return [value for value in values if value == value]


def read_stm_CLUTO(file):
    lines = Path(file).read_text().splitlines()
    rows = []
    for line in lines:
        tokens = [float(part) for part in line.split()]
        rows.append(_na_omit(tokens))
    header = rows[0]
    nrow = int(header[0])
    ncol = int(header[1])
    count = header[2]
    body = rows[1:]
    lengths = [len(line) for line in body]
    flat = [item for line in body for item in line]
    i = np.repeat(np.arange(1, nrow + 1), np.array(lengths) // 2)
    j = np.array(flat[0::2], dtype=int)
    v = np.array(flat[1::2], dtype=float)
    if count != v.size:
        raise ValueError("invalid matrix format")
    matrix = simple_triplet_matrix(i, j, v, nrow, ncol)
    path = str(file)
    labels = path + ".clabel"
    if os.path.exists(labels):
        lines = Path(labels).read_text().splitlines()
        if len(lines) == ncol:
            matrix.dimnames = [None, lines]
    labels = path + ".rlabel"
    if os.path.exists(labels):
        lines = Path(labels).read_text().splitlines()
        if len(lines) == nrow:
            if matrix.dimnames is None:
                matrix.dimnames = [lines, None]
            else:
                matrix.dimnames[0] = lines
    return matrix


def write_stm_CLUTO(x, file):
    matrix = as_simple_triplet_matrix(x)
    header = f"{matrix.nrow} {matrix.ncol} {matrix.v.size}"
    content = []
    for row in range(1, matrix.nrow + 1):
        mask = matrix.i == row
        if not np.any(mask):
            continue
        pairs = [
            f"{_r_token(column)} {_r_token(value)}"
            for column, value in zip(matrix.j[mask], matrix.v[mask])
        ]
        content.append(" ".join(pairs))
    Path(file).write_text("\n".join([header, *content]) + "\n")
    return None


def read_stm_MC(file, scalingtype=None):
    dim = np.loadtxt(f"{file}_dim", dtype=float)
    nrow = int(dim[0])
    ncol = int(dim[1])
    rows = np.loadtxt(f"{file}_row_ccs", dtype=int)
    pointers = np.loadtxt(f"{file}_col_ccs", dtype=int)
    if scalingtype is None:
        patterns = [
            a + b + c + d
            for a in "tl"
            for b in "xfe1"
            for c in "xn1"
            for d in ("", "i")
        ]
    else:
        patterns = [scalingtype]
    chosen = None
    for pattern in patterns:
        path = f"{file}_{pattern}_nz"
        if os.path.exists(path):
            chosen = pattern
            values = np.loadtxt(path, dtype=float)
            break
    if chosen is None:
        raise FileNotFoundError(file)
    values = np.atleast_1d(values)
    rows = np.atleast_1d(rows)
    pointers = np.atleast_1d(pointers)
    if int(dim[2]) != values.size:
        raise ValueError("invalid matrix format")
    columns = np.repeat(np.arange(1, ncol + 1), np.diff(pointers))
    matrix = simple_triplet_matrix(rows + 1, columns, values, nrow, ncol)
    return matrix


def write_stm_MC(x, file):
    matrix = transpose(as_simple_triplet_matrix(x))
    order = np.lexsort((matrix.i, matrix.j))
    Path(f"{file}_dim").write_text(f"{matrix.nrow} {matrix.ncol} {matrix.v.size}\n")
    Path(f"{file}_row_ccs").write_text(
        "\n".join(str(int(item) - 1) for item in matrix.i[order]) + "\n"
    )
    counts = np.bincount(matrix.j[order], minlength=matrix.ncol + 1)[1:]
    pointers = np.concatenate([[0], np.cumsum(counts)])
    Path(f"{file}_col_ccs").write_text("\n".join(str(int(item)) for item in pointers) + "\n")
    Path(f"{file}_tfn_nz").write_text("\n".join(_r_token(item) for item in matrix.v[order]) + "\n")
    return None
