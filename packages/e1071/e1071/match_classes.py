"""Label matching for square contingency tables (e1071 ``matchClasses``)."""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path
from typing import Any, Sequence

from e1071.patterns import permutations

_METHODS = ("rowmax", "greedy", "exact")


def _boot_sample_int():
    try:
        from boot.rng import sample_int
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int
    return sample_int


def _pmatch(value: Any, choices: Sequence[str]) -> int | None:
    if isinstance(value, str):
        lower = value.lower()
        for index, choice in enumerate(choices):
            if choice.lower().startswith(lower):
                return index + 1
    return None


def _as_matrix(tab: Any) -> list[list[float]]:
    if not tab:
        return [[]]
    if isinstance(tab[0], (list, tuple)):
        return [[float(value) for value in row] for row in tab]
    raise ValueError("tab must be a two-dimensional table")


def _which_max(values: Sequence[float]) -> int:
    best = 0
    best_value = values[0]
    for index in range(1, len(values)):
        if values[index] > best_value:
            best = index
            best_value = values[index]
    return best + 1


def _column_names(tab: list[list[float]], colnames: Sequence[Any] | None) -> list[Any]:
    ncol = len(tab[0])
    if colnames is not None:
        return list(colnames)
    return list(range(1, ncol + 1))


def _row_names(tab: list[list[float]], rownames: Sequence[Any] | None) -> list[Any]:
    nrow = len(tab)
    if rownames is not None:
        return list(rownames)
    return list(range(1, nrow + 1))


def _diag_agreement(matrix: list[list[float]], retval: Sequence[Any]) -> float:
    total = sum(sum(row) for row in matrix)
    return sum(matrix[i][int(retval[i]) - 1] for i in range(len(matrix))) / total


def _myseq_minus(myseq: Sequence[int], remove: Sequence[int]) -> list[int]:
    drop = set(int(value) for value in remove)
    return [value for index, value in enumerate(myseq, start=1) if index not in drop]


def match_classes(
    tab,
    method: str = "rowmax",
    iter: int = 1,
    maxexact: int = 9,
    verbose: bool = True,
    *,
    rownames: Sequence[Any] | None = None,
    colnames: Sequence[Any] | None = None,
):
    """Map row labels to column labels to maximize agreement on ``tab``."""
    matrix = _as_matrix(tab)
    nrow = len(matrix)
    ncol = len(matrix[0]) if matrix else 0
    if any(len(row) != ncol for row in matrix):
        raise ValueError("tab must be a rectangular table")

    method_code = _pmatch(method, _METHODS)
    if method_code is None:
        raise ValueError("invalid method")

    myseq = list(range(1, ncol + 1))
    cn = _column_names(matrix, colnames)
    rn = _row_names(matrix, rownames)

    rmax = [_which_max(row) for row in matrix]

    if method_code == 1:
        retval = list(rmax)
    elif method_code in (2, 3):
        if ncol != nrow:
            raise ValueError("Unique matching only for square tables.")

        cmax = [_which_max([matrix[row][col] for row in range(nrow)]) for col in range(ncol)]
        retval: list[Any] = [math.nan] * ncol
        baseok = [cmax[rmax[index] - 1] == myseq[index] for index in range(ncol)]

        for k in range(ncol):
            if not baseok[k]:
                continue
            row_index = k
            col_index = rmax[k] - 1
            therow = [matrix[row_index][col] for col in range(ncol) if col != rmax[k] - 1]
            thecol = [matrix[row][col_index] for row in range(nrow) if row != k]
            pair_sums = [a + b for a in therow for b in thecol]
            if max(pair_sums) < matrix[row_index][col_index]:
                retval[k] = rmax[k]
            else:
                baseok[k] = False

        if verbose:
            print(f"Direct agreement: {sum(baseok)} of {ncol} pairs")

        if not all(baseok):
            perm: list[list[int]] | None = None
            if method_code == 3:
                n_rest = ncol - sum(baseok)
                if n_rest > maxexact:
                    method_code = 2
                    warnings.warn(
                        f"Would need permutation of {n_rest} numbers, resetting to greedy search\n",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                else:
                    iter_count = math.gamma(n_rest + 1)
                    iter = int(round(iter_count))
                    if verbose:
                        print(f"Iterations for permutation matching: {iter} ")
                    perm = permutations(n_rest)

            if any(baseok):
                fixed = [retval[index] for index in range(ncol) if baseok[index]]
                rest = _myseq_minus(myseq, fixed)
            else:
                rest = list(myseq)

            oldagree = 0.0
            for l in range(iter):
                newretval = list(retval)
                if method_code == 2:
                    ok = list(baseok)
                    sample_int = _boot_sample_int()
                    while sum(not flag for flag in ok) > 1:
                        open_rows = [value for value in myseq if not ok[value - 1]]
                        pick = sample_int(len(open_rows), 1)[0] - 1
                        k = open_rows[pick]
                        used_cols = [
                            int(newretval[index])
                            for index in range(ncol)
                            if ok[index] and not (isinstance(newretval[index], float) and math.isnan(newretval[index]))
                        ]
                        if any(ok):
                            candidates = [
                                (col + 1, matrix[k - 1][col])
                                for col in range(ncol)
                                if (col + 1) not in used_cols
                            ]
                        else:
                            candidates = [(col + 1, matrix[k - 1][col]) for col in range(ncol)]
                        best_col = max(candidates, key=lambda item: item[1])[0]
                        newretval[k - 1] = best_col
                        ok[k - 1] = True
                    open_rows = [index + 1 for index, flag in enumerate(ok) if not flag]
                    used_cols = [
                        int(newretval[index])
                        for index in range(ncol)
                        if ok[index] and not (isinstance(newretval[index], float) and math.isnan(newretval[index]))
                    ]
                    free_cols = _myseq_minus(myseq, used_cols)
                    newretval[open_rows[0] - 1] = free_cols[0]
                else:
                    if perm is None:
                        raise RuntimeError("permutation table missing")
                    mapping = [rest[value - 1] for value in perm[l]]
                    targets = [index for index, flag in enumerate(baseok) if not flag]
                    for index, value in zip(targets, mapping):
                        newretval[index] = value

                agree = _diag_agreement(matrix, newretval)
                if l > 0:
                    if agree > oldagree:
                        retval = newretval
                        oldagree = agree
                else:
                    retval = newretval
                    oldagree = agree

    if verbose:
        pct = round(100 * _diag_agreement(matrix, retval), 2)
        print(f"Cases in matched pairs: {pct} %")

    if any(str(value) != str(cn[index]) for index, value in enumerate(myseq)):
        retval = [cn[int(value) - 1] for value in retval]

    return {str(rn[index]): retval[index] for index in range(len(retval))}
