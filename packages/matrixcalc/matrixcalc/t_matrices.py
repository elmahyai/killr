"""List of T matrices, from matrixcalc 1.0-6."""

from __future__ import annotations

from matrixcalc.e_matrices import e_matrices

_MISSING = object()


def t_matrices(n=_MISSING):
    """Return nested T matrices built from ``E.matrices``.

    Component ``result[i][j]`` is ``E[i][j]`` when ``i == j``, otherwise
    ``E[i][j] + E[j][i]``. The argument must be an integer at least 2.
    """
    if n is _MISSING:
        raise ValueError("argument n is missing")
    e_blocks = e_matrices(n)
    order = len(e_blocks)
    blocks = []
    for i in range(order):
        row = []
        for j in range(order):
            if i == j:
                row.append(e_blocks[i][j])
            else:
                row.append(e_blocks[i][j] + e_blocks[j][i])
        blocks.append(row)
    return blocks
