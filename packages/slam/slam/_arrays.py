"""Simple triplet matrices and simple sparse arrays from slam 0.1-56."""

import numpy as np

from slam.options import slam_options


class SimpleTripletMatrix:
    """i and j are 1-based. Implicit entries are zero."""

    def __init__(self, i, j, v, nrow, ncol, dimnames=None):
        self.i = np.asarray(i, dtype=int).reshape(-1)
        self.j = np.asarray(j, dtype=int).reshape(-1)
        self.v = np.asarray(v, dtype=float).reshape(-1)
        self.nrow = int(nrow)
        self.ncol = int(ncol)
        self.dimnames = dimnames
        if self.i.size != self.j.size or self.i.size != self.v.size:
            raise ValueError("'i, j, v' different lengths")
        if self.nrow < 0 or self.ncol < 0:
            raise ValueError("'nrow, ncol' invalid")
        if self.i.size and (
            np.any(self.i < 1)
            or np.any(self.i > self.nrow)
            or np.any(self.j < 1)
            or np.any(self.j > self.ncol)
        ):
            raise ValueError("'i, j' invalid")
        pairs = np.stack([self.i, self.j], axis=1) if self.i.size else np.zeros((0, 2), dtype=int)
        if pairs.shape[0] != np.unique(pairs, axis=0).shape[0]:
            raise ValueError("Duplicate (i, j) pairs are not allowed.")

    def __repr__(self):
        return f"A {self.nrow}x{self.ncol} simple triplet matrix."


class SimpleSparseArray:
    """i is an (nnz, ndim) matrix of 1-based subscripts."""

    def __init__(self, i, v, dim, dimnames=None):
        index = np.asarray(i, dtype=int)
        if index.ndim == 1:
            index = index.reshape(-1, 1)
        self.i = index
        self.v = np.asarray(v, dtype=float).reshape(-1)
        self.dim = np.asarray(dim, dtype=int).reshape(-1)
        self.dimnames = dimnames
        if self.i.shape[0] != self.v.size:
            raise ValueError("'i, v' invalid length")
        if self.i.shape[1] != self.dim.size:
            raise ValueError("'i, dim' invalid length")
        rows = {tuple(row) for row in self.i.tolist()}
        if len(rows) != self.i.shape[0]:
            raise ValueError("Duplicate rows in i are not allowed.")
        for axis, size in enumerate(self.dim):
            if size < 0:
                raise ValueError("'dim' invalid")
            if size == 0 and self.i.shape[0]:
                raise ValueError("'dim, i' invalid number of rows")
            if size > 0 and self.i.shape[0] and (
                np.any(self.i[:, axis] < 1) or np.any(self.i[:, axis] > size)
            ):
                raise ValueError("i invalid")

    def __repr__(self):
        shown = "x".join(str(int(part)) for part in self.dim)
        return f"A simple sparse array of dimension {shown}."


def simple_triplet_matrix(i, j, v, nrow=None, ncol=None, dimnames=None):
    ii = np.asarray(i, dtype=int).reshape(-1)
    jj = np.asarray(j, dtype=int).reshape(-1)
    if nrow is None:
        nrow = int(ii.max()) if ii.size else 0
    if ncol is None:
        ncol = int(jj.max()) if jj.size else 0
    return SimpleTripletMatrix(ii, jj, v, nrow, ncol, dimnames)


def is_simple_triplet_matrix(x):
    return isinstance(x, SimpleTripletMatrix)


def simple_triplet_zero_matrix(nrow, ncol=None, mode="double"):
    if ncol is None:
        ncol = nrow
    return simple_triplet_matrix([], [], [], int(nrow), int(ncol))


def simple_triplet_diag_matrix(v, nrow=None):
    values = np.asarray(v, dtype=float).reshape(-1)
    if nrow is None:
        nrow = values.size
    nrow = int(nrow)
    if values.size == 0:
        values = np.zeros(nrow)
    elif values.size != nrow:
        values = np.resize(values, nrow)
    index = np.arange(1, nrow + 1)
    return simple_triplet_matrix(index, index, values, nrow, nrow)


def _from_dense(array, dimnames=None):
    dense = np.asarray(array, dtype=float)
    if dense.ndim == 1:
        dense = dense.reshape(-1, 1)
    nrow, ncol = dense.shape
    flat = np.ravel(dense, order="F")
    keep = np.flatnonzero(np.isnan(flat) | (flat != 0))
    if keep.size == 0:
        return simple_triplet_matrix([], [], [], nrow, ncol, dimnames)
    rows = keep % nrow + 1
    cols = keep // nrow + 1
    return simple_triplet_matrix(rows, cols, flat[keep], nrow, ncol, dimnames)


def as_simple_triplet_matrix(x):
    if isinstance(x, SimpleTripletMatrix):
        return x
    if isinstance(x, SimpleSparseArray):
        if x.dim.size == 1:
            return simple_triplet_matrix(
                x.i[:, 0],
                np.ones(x.v.size, dtype=int),
                x.v,
                int(x.dim[0]),
                1,
                None if x.dimnames is None else list(x.dimnames) + [None],
            )
        if x.dim.size != 2:
            raise ValueError("Unsupported number of dimensions")
        return simple_triplet_matrix(
            x.i[:, 0], x.i[:, 1], x.v, int(x.dim[0]), int(x.dim[1]), x.dimnames
        )
    return _from_dense(x)


def as_matrix(x):
    if not isinstance(x, SimpleTripletMatrix):
        return np.asarray(x, dtype=float)
    out = np.zeros((x.nrow, x.ncol), dtype=float)
    if x.v.size:
        out[x.i - 1, x.j - 1] = x.v
    return out


def transpose(x):
    names = None if x.dimnames is None else list(reversed(x.dimnames))
    return simple_triplet_matrix(x.j, x.i, x.v, x.ncol, x.nrow, names)


def _subset_columns(x, kept):
    kept = np.asarray(kept, dtype=int).reshape(-1)
    if kept.size and np.any(kept < 0):
        if np.any(kept > 0):
            raise ValueError("Cannot mix positive and negative subscripts.")
        dropped = {-int(item) for item in kept}
        kept = np.array(
            [column for column in range(1, x.ncol + 1) if column not in dropped],
            dtype=int,
        )
    mapping = np.zeros(x.ncol + 1, dtype=int)
    mapping[kept] = np.arange(1, kept.size + 1)
    pos = mapping[x.j] > 0
    names = x.dimnames
    if names is not None and names[1] is not None:
        names = [names[0], [names[1][item - 1] for item in kept]]
    return simple_triplet_matrix(
        x.i[pos], mapping[x.j[pos]], x.v[pos], x.nrow, int(kept.size), names
    )


def _sums(x, margin, na_rm=False):
    x = as_simple_triplet_matrix(x)
    length = x.nrow if margin == 1 else x.ncol
    index = x.i if margin == 1 else x.j
    out = np.zeros(length, dtype=float)
    if not x.v.size:
        return out
    for slot, value in zip(index, x.v):
        if na_rm and np.isnan(value):
            continue
        out[slot - 1] += value
    return out


def row_sums(x, na_rm=False, dims=1):
    if isinstance(x, SimpleTripletMatrix):
        return _sums(x, 1, na_rm)
    array = np.asarray(x, dtype=float)
    return np.nansum(array, axis=1) if na_rm else np.sum(array, axis=1)


def col_sums(x, na_rm=False, dims=1):
    if isinstance(x, SimpleTripletMatrix):
        return _sums(x, 2, na_rm)
    array = np.asarray(x, dtype=float)
    return np.nansum(array, axis=0) if na_rm else np.sum(array, axis=0)


def _means(x, margin, na_rm=False):
    totals = _sums(x, margin, na_rm)
    count = x.ncol if margin == 1 else x.nrow
    if na_rm:
        flags = simple_triplet_matrix(x.i, x.j, np.isnan(x.v).astype(float), x.nrow, x.ncol)
        missing = _sums(flags, margin, False)
        count = count - missing
    return totals / count


def row_means(x, na_rm=False, dims=1):
    if isinstance(x, SimpleTripletMatrix):
        return _means(x, 1, na_rm)
    array = np.asarray(x, dtype=float)
    return np.nanmean(array, axis=1) if na_rm else np.mean(array, axis=1)


def col_means(x, na_rm=False, dims=1):
    if isinstance(x, SimpleTripletMatrix):
        return _means(x, 2, na_rm)
    array = np.asarray(x, dtype=float)
    return np.nanmean(array, axis=0) if na_rm else np.mean(array, axis=0)


def _power(x, exponent):
    if not np.isfinite(exponent) or exponent <= 0:
        raise ValueError("Not implemented.")
    return simple_triplet_matrix(x.i, x.j, x.v ** exponent, x.nrow, x.ncol, x.dimnames)


def _absolute(x):
    return simple_triplet_matrix(x.i, x.j, np.abs(x.v), x.nrow, x.ncol, x.dimnames)


def row_norms(x, p=2):
    x = as_simple_triplet_matrix(x)
    if p == 2:
        return np.sqrt(row_sums(_power(x, 2)))
    if p == 1:
        return row_sums(_absolute(x))
    if p == np.inf:
        return np.ravel(as_matrix(rollup(_absolute(x), 2, fun=np.max)), order="F")
    return row_sums(_power(_absolute(x), p)) ** (1 / p)


def col_norms(x, p=2):
    x = as_simple_triplet_matrix(x)
    if p == 2:
        return np.sqrt(col_sums(_power(x, 2)))
    if p == 1:
        return col_sums(_absolute(x))
    if p == np.inf:
        return np.ravel(as_matrix(rollup(_absolute(x), 1, fun=np.max)), order="F")
    return col_sums(_power(_absolute(x), p)) ** (1 / p)


def _column_blocks(x):
    order = np.argsort(x.j, kind="mergesort")
    columns = x.j[order]
    rows = x.i[order]
    values = x.v[order]
    bounds = np.zeros(x.ncol + 1, dtype=int)
    if columns.size:
        counts = np.bincount(columns, minlength=x.ncol + 1)
        bounds[1:] = np.cumsum(counts[1:])
    return rows, values, bounds


def _tcrossprod_stm(x, y=None):
    if y is not None and x.ncol != y.ncol:
        raise ValueError("the number of columns of 'x' and 'y' do not conform")
    if not np.all(np.isfinite(x.v)) or (y is not None and not np.all(np.isfinite(y.v))):
        left = as_matrix(x)
        right = left if y is None else as_matrix(y)
        return left @ right.T
    n = x.nrow
    m = n if y is None else y.nrow
    result = np.zeros((n, m), dtype=float)
    rows, values, bounds = _column_blocks(x)
    if x.ncol == 0 or n == 0 or values.size == 0 or (y is not None and (m == 0 or y.v.size == 0)):
        return result
    if y is None:
        for column in range(x.ncol):
            start, stop = int(bounds[column]), int(bounds[column + 1])
            for right in range(start, stop):
                scale = values[right]
                row_right = int(rows[right]) - 1
                for left in range(start, right + 1):
                    result[int(rows[left]) - 1, row_right] += values[left] * scale
        for row in range(1, n):
            result[row, :row] += result[:row, row]
            result[:row, row] = result[row, :row]
        return result
    for row_y, column, value in zip(y.i, y.j, y.v):
        start, stop = int(bounds[int(column) - 1]), int(bounds[int(column)])
        slot = int(row_y) - 1
        for left in range(start, stop):
            result[int(rows[left]) - 1, slot] += values[left] * value
    return result


def tcrossprod_simple_triplet_matrix(x, y=None):
    if is_simple_triplet_matrix(x):
        return _tcrossprod_stm(x, None if y is None else as_simple_triplet_matrix(y))
    if is_simple_triplet_matrix(y):
        return _tcrossprod_stm(y, as_simple_triplet_matrix(as_matrix(x))).T
    raise ValueError("neither 'x' nor 'y' of class 'simple_triplet_matrix'")


def crossprod_simple_triplet_matrix(x, y=None):
    if is_simple_triplet_matrix(x):
        other = None if y is None else transpose(as_simple_triplet_matrix(y))
        return _tcrossprod_stm(transpose(x), other)
    if is_simple_triplet_matrix(y):
        return _tcrossprod_stm(transpose(y), transpose(as_simple_triplet_matrix(as_matrix(x)))).T
    raise ValueError("neither 'x' nor 'y' of class 'simple_triplet_matrix'")


def matprod_simple_triplet_matrix(x, y):
    if is_simple_triplet_matrix(x):
        return _tcrossprod_stm(x, transpose(as_simple_triplet_matrix(y)))
    if is_simple_triplet_matrix(y):
        return _tcrossprod_stm(transpose(y), as_simple_triplet_matrix(as_matrix(x))).T
    raise ValueError("neither 'x' nor 'y' of class 'simple_triplet_matrix'")


def _column_vector(x, column):
    out = np.zeros(x.nrow, dtype=float)
    mask = x.j == column
    if np.any(mask):
        out[x.i[mask] - 1] = x.v[mask]
    return out


def colapply_simple_triplet_matrix(x, fun, *args):
    if not is_simple_triplet_matrix(x):
        raise ValueError("'x' not of class simple_triplet_matrix")
    pieces = [fun(_column_vector(x, column), *args) for column in range(1, x.ncol + 1)]
    if pieces and all(np.asarray(piece).size == 1 for piece in pieces):
        return np.array([float(np.asarray(piece).reshape(-1)[0]) for piece in pieces])
    return pieces


def rowapply_simple_triplet_matrix(x, fun, *args):
    if not is_simple_triplet_matrix(x):
        raise ValueError("'x' not of class simple_striplet_matrix")
    return colapply_simple_triplet_matrix(transpose(x), fun, *args)


def _symmetrize_packed(packed, n):
    mask = np.ravel(np.tri(n, dtype=bool), order="F")
    extended = np.full(n * n, np.nan)
    extended[: packed.size] = packed
    extended[mask] = packed
    square = np.reshape(extended, (n, n))
    flat = np.ravel(square, order="F")
    mirrored = np.ravel(square.T, order="F")
    flat[mask] = mirrored[mask]
    return np.reshape(flat, (n, n), order="F")


def crossapply_simple_triplet_matrix(x, y=None, fun=None, *args):
    if y is None:
        state = {"Y": x}
        pieces = []
        for column in range(1, x.ncol + 1):
            current = _column_vector(x, column)
            pieces.append(
                colapply_simple_triplet_matrix(
                    state["Y"], lambda other, left=current: fun(other, left, *args)
                )
            )
            state["Y"] = _subset_columns(state["Y"], -1)
        flat = np.concatenate([np.atleast_1d(np.asarray(piece, dtype=float)) for piece in pieces])
        return _symmetrize_packed(flat, x.ncol)
    if is_simple_triplet_matrix(y):
        if not is_simple_triplet_matrix(x):
            swapped = crossapply_simple_triplet_matrix(
                y, as_matrix(x), lambda right, left: fun(left, right, *args)
            )
            return swapped.T
        if x.nrow != y.nrow:
            raise ValueError("the numer of rows of 'x' and 'y' do not conform")
        if x.ncol > y.ncol:
            swapped = crossapply_simple_triplet_matrix(
                y, x, lambda right, left: fun(left, right, *args)
            )
            return swapped.T
        pieces = [
            colapply_simple_triplet_matrix(
                y, lambda other, left=_column_vector(x, column): fun(left, other, *args)
            )
            for column in range(1, x.ncol + 1)
        ]
        flat = np.concatenate([np.atleast_1d(np.asarray(piece, dtype=float)) for piece in pieces])
        return np.reshape(flat, (x.ncol, y.ncol))
    y = as_matrix(y)
    if x.nrow != y.shape[0]:
        raise ValueError("the numer of rows of 'x' and 'y' do not conform")
    pieces = []
    for column in range(1, x.ncol + 1):
        left = _column_vector(x, column)
        pieces.append(np.array([fun(left, y[:, index], *args) for index in range(y.shape[1])], dtype=float))
    flat = np.concatenate(pieces)
    return np.reshape(flat, (x.ncol, y.shape[1]))


def tcrossapply_simple_triplet_matrix(x, y=None, fun=None, *args):
    if is_simple_triplet_matrix(x):
        other = None if y is None else transpose(as_simple_triplet_matrix(y) if is_simple_triplet_matrix(y) else as_matrix(y))
        return crossapply_simple_triplet_matrix(transpose(x), other, fun, *args)
    if is_simple_triplet_matrix(y):
        return crossapply_simple_triplet_matrix(transpose(as_matrix(x)), transpose(y), fun, *args)
    raise ValueError("'x, y' not of class simple_triplet_matrix")


def _factor(values, length):
    if values is None:
        codes = np.ones(length, dtype=int)
        levels = ["1"]
        return codes, levels
    labels = [str(item) for item in values]
    if len(labels) != length:
        raise ValueError("INDEX invalid length")
    levels = sorted(set(labels), key=labels.index)
    # R as.factor sorts unique values for numeric and character in the order of appearance? 
    # as.factor on character sorts? factor() sorts levels by default for character via sort.
    levels = sorted(set(labels))
    mapping = {label: index + 1 for index, label in enumerate(levels)}
    codes = np.array([mapping[label] for label in labels], dtype=int)
    return codes, levels


def _row_tsums(x, codes, levels, na_rm=False):
    totals = {}
    for row, column, value in zip(x.i, x.j, x.v):
        group = int(codes[int(column) - 1])
        if na_rm and np.isnan(value):
            continue
        key = (int(row), group)
        totals[key] = totals.get(key, 0.0) + (0.0 if np.isnan(value) and not na_rm else float(value))
        if np.isnan(value) and not na_rm:
            totals[key] = np.nan
    rows, cols, values = [], [], []
    for (row, group), value in totals.items():
        rows.append(row)
        cols.append(group)
        values.append(value)
    names = [x.dimnames[0] if x.dimnames else None, levels]
    return simple_triplet_matrix(rows, cols, values, x.nrow, len(levels), names)


def rollup(x, margin, index=None, fun=None, drop=False, reduce=False, na_rm=False):
    if fun is None:
        fun = np.sum
    if isinstance(x, SimpleTripletMatrix) and fun in (np.sum, sum):
        margins = [margin] if np.ndim(margin) == 0 else list(margin)
        current = x
        groups = index
        if groups is None:
            groups = [None] * len(margins)
        elif np.ndim(groups) != 0 and not isinstance(groups, (list, tuple)):
            groups = [groups]
        if len(groups) != len(margins):
            raise ValueError("'INDEX' invalid length")
        for slot, group in zip(margins, groups):
            if int(slot) == 1:
                current = transpose(
                    rollup(transpose(current), 2, None if group is None else [group], fun, na_rm=na_rm)
                )
            else:
                codes, levels = _factor(group, current.ncol)
                current = _row_tsums(current, codes, levels, na_rm)
        return current
    if isinstance(x, SimpleTripletMatrix):
        return as_simple_triplet_matrix(
            rollup(as_simple_sparse_array(x), margin, index, fun, drop=drop)
        )
    if isinstance(x, SimpleSparseArray):
        return _rollup_ssa(x, margin, index, fun, drop)
    return _rollup_array(np.asarray(x, dtype=float), margin, index, fun, drop)


def _rollup_ssa(x, margin, index, fun, drop):
    """Group stored entries. Implicit zeros stay out of FUN."""
    margins = [int(margin)] if np.ndim(margin) == 0 else [int(item) for item in margin]
    if index is None:
        groups = [None] * len(margins)
    elif isinstance(index, (list, tuple)):
        groups = list(index)
    else:
        groups = [index]
    if len(groups) != len(margins):
        raise ValueError("'INDEX' invalid length")
    dim = np.array(x.dim, copy=True)
    index_mat = np.array(x.i, copy=True)
    values = np.array(x.v, copy=True)
    for slot, group in zip(margins, groups):
        axis = slot - 1
        codes, _levels = _factor(group, int(dim[axis]))
        if index_mat.shape[0]:
            index_mat[:, axis] = codes[index_mat[:, axis] - 1]
        dim[axis] = len(_levels)
    buckets = {}
    for row, value in zip(index_mat.tolist(), values.tolist()):
        buckets.setdefault(tuple(int(part) for part in row), []).append(value)
    new_index = []
    new_values = []
    for key, grouped in buckets.items():
        result = np.atleast_1d(np.asarray(fun(np.asarray(grouped, dtype=float)), dtype=float))
        if result.size != 1:
            raise ValueError("FUN result length is not 1")
        if result[0] == 0:
            continue
        new_index.append(key)
        new_values.append(float(result[0]))
    if new_index:
        built = simple_sparse_array(np.array(new_index, dtype=int), new_values, dim, None)
    else:
        built = simple_sparse_array(np.zeros((0, dim.size), dtype=int), [], dim, None)
    if drop:
        return drop_simple_sparse_array(built)
    return built


def _linear_index(dim, index):
    """1-based column-major positions, matching R_vector_index."""
    dim = np.asarray(dim, dtype=int)
    index = np.asarray(index, dtype=int)
    if index.ndim == 1:
        index = index.reshape(-1, 1)
    linear = index[:, 0].astype(int)
    scale = 1
    for axis in range(1, dim.size):
        linear = linear + scale * (index[:, axis] - 1)
        scale *= int(dim[axis - 1])
    return linear


def _rollup_array(array, margin, index, fun, drop):
    dense = np.asarray(array, dtype=float)
    dim = np.array(dense.shape, dtype=int)
    margins = [int(margin)] if np.ndim(margin) == 0 else [int(item) for item in margin]
    if index is None:
        groups = [None] * len(margins)
    elif isinstance(index, (list, tuple)):
        groups = list(index)
    else:
        groups = [index]
    positions = np.array(np.unravel_index(np.arange(dense.size), dense.shape, order="F")).T + 1
    new_dim = dim.copy()
    for slot, group in zip(margins, groups):
        axis = slot - 1
        codes, levels = _factor(group, int(dim[axis]))
        positions[:, axis] = codes[positions[:, axis] - 1]
        new_dim[axis] = len(levels)
    linear = _linear_index(new_dim, positions)
    values = np.ravel(dense, order="F")
    reduced = []
    for code in range(1, int(np.prod(new_dim)) + 1):
        reduced.append(fun(values[linear == code]))
    out = np.reshape(np.array(reduced, dtype=float), new_dim, order="F")
    if drop:
        out = np.squeeze(out)
    return out


def simple_sparse_array(i, v, dim=None, dimnames=None):
    index = np.asarray(i, dtype=int)
    if index.ndim == 1:
        index = index.reshape(-1, 1)
    if dim is None:
        dim = index.max(axis=0) if index.shape[0] else np.array([0, 0], dtype=int)
    return SimpleSparseArray(index, v, dim, dimnames)


def is_simple_sparse_array(x):
    return isinstance(x, SimpleSparseArray)


def as_simple_sparse_array(x):
    if isinstance(x, SimpleSparseArray):
        return x
    if isinstance(x, SimpleTripletMatrix):
        if x.v.size == 0:
            index = np.zeros((0, 2), dtype=int)
        else:
            index = np.column_stack([x.i, x.j])
        return simple_sparse_array(index, x.v, [x.nrow, x.ncol], x.dimnames)
    dense = np.asarray(x, dtype=float)
    flat = np.ravel(dense, order="F")
    keep = np.flatnonzero(np.isnan(flat) | (flat != 0))
    if keep.size == 0:
        index = np.zeros((0, dense.ndim), dtype=int)
    else:
        coords = np.array(np.unravel_index(keep, dense.shape, order="F")).T + 1
        index = coords
    return simple_sparse_array(index, flat[keep] if keep.size else [], dense.shape)


def as_array(x):
    if isinstance(x, SimpleTripletMatrix):
        return as_matrix(x)
    out = np.zeros(tuple(int(part) for part in x.dim), dtype=float)
    if x.v.size:
        slots = tuple(x.i[:, axis] - 1 for axis in range(x.i.shape[1]))
        out[slots] = x.v
    return out


def reduce_simple_sparse_array(x, strict=False, order=False):
    index = np.array(x.i, copy=True)
    values = np.array(x.v, copy=True)
    if values.size:
        keys = [tuple(row) for row in index.tolist()]
        groups = {}
        for slot, key in enumerate(keys):
            groups.setdefault(key, []).append(slot)
        if any(len(slots) > 1 for slots in groups.values()):
            if strict:
                raise ValueError("multiple entries")
            new_index = []
            new_values = []
            warned = False
            for key, slots in groups.items():
                chosen = values[slots]
                unique = np.unique(chosen)
                if unique.size > 1:
                    warned = True
                    new_values.append(np.nan)
                else:
                    new_values.append(float(unique[0]))
                new_index.append(key)
            index = np.array(new_index, dtype=int)
            values = np.array(new_values, dtype=float)
        zeros = np.flatnonzero(values == 0)
        if zeros.size:
            if strict:
                raise ValueError("zero entries")
            keep = np.ones(values.size, dtype=bool)
            keep[zeros] = False
            values = values[keep]
            index = index[keep]
        if order and values.size:
            rank = np.lexsort(index.T)
            values = values[rank]
            index = index[rank]
    return simple_sparse_array(index, values, x.dim, x.dimnames)


def drop_simple_sparse_array(x):
    dim = np.array(x.dim, copy=True)
    if np.any(dim == 0):
        return np.zeros(0, dtype=float)
    singleton = np.flatnonzero(dim == 1)
    if singleton.size == dim.size:
        return np.array(x.v, copy=True)
    if singleton.size:
        keep = np.ones(dim.size, dtype=bool)
        keep[singleton] = False
        index = x.i[:, keep]
        names = None if x.dimnames is None else [x.dimnames[slot] for slot in np.flatnonzero(keep)]
        return simple_sparse_array(index, x.v, dim[keep], names)
    return x


def simplify_simple_sparse_array(x, higher=True):
    return x


def _extend_once(x, slot):
    """Prepend a size-1 margin, then move it with R's order() permutation."""
    dim = np.concatenate([[1], np.asarray(x.dim, dtype=int)])
    width = x.i.shape[1] if x.i.ndim == 2 else 0
    if x.i.shape[0] == 0:
        index = np.zeros((0, width + 1), dtype=int)
    else:
        index = np.column_stack([np.ones(x.i.shape[0], dtype=int), x.i])
    if slot > 0:
        if slot > dim.size:
            raise ValueError("'MARGIN' invalid")
        positions = np.array([slot + 1] + list(range(1, dim.size)), dtype=int)
        permutation = np.argsort(positions, kind="mergesort")
        dim = dim[permutation]
        index = index[:, permutation]
    return simple_sparse_array(index, x.v, dim, None)


def extend_simple_sparse_array(x, margin=0):
    if not is_simple_sparse_array(x):
        raise ValueError("'x' not of class 'simple_sparse_array'")
    margins = [int(margin)] if np.ndim(margin) == 0 else [int(item) for item in np.atleast_1d(margin)]
    if not margins:
        margins = [0]
    adjusted = []
    for item in margins:
        adjusted.append(-item - 1 if item < 0 else item)
    slot = adjusted[0]
    current = _extend_once(x, slot)
    rest = adjusted[1:]
    while rest:
        rest = [item + 1 if item > slot else item for item in rest]
        current = extend_simple_sparse_array(current, rest[0])
        rest = rest[1:]
    return current


def abind_simple_sparse_array(*args, margin=1):
    items = [item for item in args if item is not None]
    if not items:
        return None
    current = as_simple_sparse_array(items[0])
    if margin < 0:
        current = extend_simple_sparse_array(current, margin)
    if len(items) == 1:
        return current
    for item in items[1:]:
        other = as_simple_sparse_array(item)
        if margin < 0:
            other = extend_simple_sparse_array(other, margin)
        axis = min(abs(int(margin)), current.dim.size) - 1
        if other.dim.size == current.dim.size - 1:
            other = extend_simple_sparse_array(other, -(axis + 1))
        elif current.dim.size == other.dim.size - 1:
            current = extend_simple_sparse_array(current, -(min(abs(int(margin)), other.dim.size)))
            axis = min(abs(int(margin)), current.dim.size) - 1
        elif other.dim.size != current.dim.size:
            raise ValueError("lengths of 'dim' do not conform")
        if not np.array_equal(np.delete(other.dim, axis), np.delete(current.dim, axis)):
            raise ValueError("common parts of 'dim' do not conform")
        added = np.array(other.i, copy=True)
        added[:, axis] += int(current.dim[axis])
        index = np.vstack([current.i, added]) if current.i.size or added.size else current.i
        values = np.concatenate([current.v, other.v])
        dim = np.array(current.dim, copy=True)
        dim[axis] += int(other.dim[axis])
        current = simple_sparse_array(index, values, dim, None)
    return current
