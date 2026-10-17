"""Lower-triangular and symmetric matrix collections from mvtnorm.

Storage is a matrix whose rows are the packed triangle and whose columns
are replicates. ``byrow`` false is column-major lower; true is row-major
lower. Attributes ``J``, ``diag``, ``byrow``, ``rcnames``, and the class
vector follow the R object.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

_EPS = float(np.finfo(np.float64).eps)
_DIM_MSG = (
    "Dimension of object does not correspond to lower \n"
    "              triangular part of a square matrix"
)
_INDEX_CACHE: dict = {}


class LtError(ValueError):
    """An error raised with the same text R would stop on."""


def stopifnot(cond, expr):
    if not cond:
        raise LtError(f"{expr} is not TRUE")


def _is_true(value):
    return value is True or value is np.True_


def _is_character(value):
    if isinstance(value, str):
        return True
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return True
    if isinstance(value, np.ndarray) and value.dtype.kind in "UOS":
        return True
    return False


def _as_character_vector(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, np.ndarray):
        return [str(item) for item in value.tolist()]
    return [str(item) for item in value]


def _unique(seq):
    seen = []
    for item in seq:
        if item not in seen:
            seen.append(item)
    return seen


def _is_numeric(value):
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, np.ndarray):
        return value.dtype.kind in "iuf" and value.dtype.kind != "b"
    if isinstance(value, (list, tuple)):
        if not value:
            return True
        return all(_is_numeric(item) for item in value)
    return False


def _is_matrix(value):
    return isinstance(value, np.ndarray) and value.ndim == 2


def _class_vector(value):
    if isinstance(value, LtMatrices):
        return list(value.rclass)
    if isinstance(value, (bool, np.bool_)):
        return ["logical"]
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return ["integer"]
    if isinstance(value, np.ndarray):
        if value.ndim == 2:
            return ["matrix", "array"]
        if value.dtype.kind in "iuf":
            return ["numeric"]
    if isinstance(value, float):
        return ["numeric"]
    return ["numeric"]


def _has_class(value, name):
    return name in _class_vector(value)


def _copy_rc(rcnames):
    if rcnames is False or rcnames is None:
        return rcnames
    return list(rcnames)


def _names_arg(value):
    rcnames = getattr(value, "rcnames", None)
    if rcnames is False:
        return False
    if rcnames is None:
        return True
    return list(rcnames)


def _packed_len(J, diag):
    J = int(J)
    if J <= 0:
        return 0
    return J * (J - 1) // 2 + (J if diag else 0)


def _infer_J(nrow, diag):
    diag_n = 1.0 if diag else 0.0
    guess = int(math.floor((1.0 + math.sqrt(1.0 + 8.0 * nrow)) / 2.0 - diag_n))
    for cand in (guess, guess - 1, guess + 1, guess - 2, guess + 2):
        if cand >= 0 and _packed_len(cand, bool(diag)) == nrow:
            return int(cand)
    raise LtError(_DIM_MSG)


def _r_matrix(data, nrow, ncol):
    flat = np.asarray(data, dtype=np.float64).ravel(order="F")
    need = int(nrow) * int(ncol)
    if need == 0:
        return np.zeros((int(nrow), int(ncol)), dtype=np.float64)
    if flat.size == 0:
        raise LtError("data length is zero")
    if need % flat.size != 0 and flat.size % need != 0:
        warnings.warn("data length differs from size of matrix", stacklevel=2)
    reps = int(math.ceil(need / flat.size))
    tiled = np.tile(flat, reps)[:need]
    return tiled.reshape((int(nrow), int(ncol)), order="F")


def _nrow(value):
    array = np.asarray(value)
    if array.ndim == 0:
        return 1
    return int(array.shape[0])


def _ncol(value):
    array = np.asarray(value)
    if array.ndim <= 1:
        return 1
    return int(array.shape[1])


class LtMatrices(np.ndarray):
    """Packed triangles, one replicate in each column."""

    def __new__(
        cls,
        data,
        J,
        diag,
        byrow,
        rcnames,
        rclass,
        rownames=None,
        colnames=None,
    ):
        array = np.array(data, dtype=np.float64, copy=True, subok=False)
        if array.ndim == 1:
            array = array.reshape((-1, 1))
        obj = array.view(cls)
        obj.J = int(J)
        obj.diag = bool(diag)
        obj.byrow = bool(byrow)
        obj.rcnames = _copy_rc(rcnames)
        obj.rclass = list(rclass)
        obj.rownames = None if rownames is None else list(rownames)
        obj.colnames = None if colnames is None else list(colnames)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.J = getattr(obj, "J", None)
        self.diag = bool(getattr(obj, "diag", False))
        self.byrow = bool(getattr(obj, "byrow", False))
        self.rcnames = _copy_rc(getattr(obj, "rcnames", None))
        rclass = getattr(obj, "rclass", None)
        self.rclass = list(rclass) if rclass is not None else ["ltMatrices", "matrix", "array"]
        rownames = getattr(obj, "rownames", None)
        colnames = getattr(obj, "colnames", None)
        self.rownames = None if rownames is None else list(rownames)
        self.colnames = None if colnames is None else list(colnames)

    def copy(self, order="C"):
        return LtMatrices(
            np.array(self, dtype=np.float64, copy=True, subok=False),
            self.J,
            self.diag,
            self.byrow,
            self.rcnames,
            self.rclass,
            self.rownames,
            self.colnames,
        )

    @property
    def dim(self):
        cols = int(self.shape[1]) if self.ndim == 2 else 1
        return (cols, int(self.J), int(self.J))

    def __repr__(self):
        n, J, _ = self.dim
        kind = self.rclass[0] if self.rclass else "ltMatrices"
        return f"{kind}(N={n}, J={J}, diag={self.diag}, byrow={self.byrow})"

    def __str__(self):
        return _format_lt(self)

    def __matmul__(self, other):
        return Mult(self, other)


def _format_lt(value):
    array = as_array(value)
    J = value.J
    pieces = [repr(value)]
    for n in range(array.shape[2]):
        pieces.append(f", , {n + 1}")
        block = array[:, :, n]
        for i in range(J):
            row = []
            for j in range(J):
                number = block[i, j]
                if number == 0.0 and not (value.diag is False and i == j):
                    if is_syMatrices(value) and not is_ltMatrices(value):
                        row.append(f"{number:.6g}")
                    elif i < j:
                        row.append(".")
                    else:
                        row.append(f"{number:.6g}")
                else:
                    row.append(f"{number:.6g}")
            pieces.append(" ".join(row))
    return "\n".join(pieces)


def _lt_dim(value):
    if isinstance(value, LtMatrices):
        return value.dim
    array = np.asarray(value)
    return tuple(int(item) for item in array.shape)


def dim(x):
    return _lt_dim(x)


def _tri_index(J, diag, byrow):
    key = (int(J), bool(diag), bool(byrow))
    cached = _INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    if J <= 0:
        pair = (np.array([], dtype=int), np.array([], dtype=int))
        _INDEX_CACHE[key] = pair
        return pair
    rows, cols = np.tril_indices(int(J), k=0 if diag else -1)
    if not byrow and rows.size:
        order = np.lexsort((rows, cols))
        rows, cols = rows[order], cols[order]
    pair = (rows, cols)
    _INDEX_CACHE[key] = pair
    return pair


def _lt(J, diag=False):
    mask = np.zeros((int(J), int(J)), dtype=bool)
    if J <= 0:
        return mask
    rows, cols = np.tril_indices(int(J), k=0 if diag else -1)
    mask[rows, cols] = True
    return mask


def _ut(J, diag=False):
    return ~_lt(J, diag=not diag)


def _to_dense(packed, J, diag, byrow):
    dense = np.eye(int(J), dtype=np.float64)
    values = np.asarray(packed, dtype=np.float64).ravel()
    if values.size == 0 or J <= 0:
        return dense
    rows, cols = _tri_index(J, diag, byrow)
    dense[rows, cols] = values
    return dense


def _pack(dense, diag, byrow):
    rows, cols = _tri_index(dense.shape[0], diag, byrow)
    if rows.size == 0:
        return np.zeros(0, dtype=np.float64)
    return np.asarray(dense[rows, cols], dtype=np.float64)


def _sym_from_lower(dense):
    lower = np.tril(dense)
    return lower + lower.T - np.diag(np.diag(lower))


def _element_names(J, diag, byrow, labels):
    names = []
    if not byrow:
        for col in range(J):
            start = col if diag else col + 1
            for row in range(start, J):
                names.append(f"{labels[row]}.{labels[col]}")
    else:
        for row in range(J):
            stop = row + 1 if diag else row
            for col in range(stop):
                names.append(f"{labels[row]}.{labels[col]}")
    return names


def _f_positions(mask):
    """Row and column of each true entry, in column-major order."""
    pos = np.flatnonzero(np.asarray(mask).ravel(order="F"))
    rows = pos % mask.shape[0]
    cols = pos // mask.shape[0]
    return rows, cols


def _set_f(matrix, mask, values):
    rows, cols = _f_positions(mask)
    matrix[rows, cols] = values
    return matrix


def _c2r(J, diag=False):
    n = J * (J + (1 if diag else -1)) // 2
    if n <= 0:
        return np.array([], dtype=int)
    rL = np.zeros((J, J), dtype=int)
    lt = _lt(J, diag=diag)
    ut = ~lt
    diagonal = np.diag(ut).copy()
    np.fill_diagonal(ut, np.logical_not(diagonal))
    _set_f(rL, lt, np.arange(1, n + 1))
    idx = rL.T.ravel(order="F")[ut.ravel(order="F")]
    return np.arange(1, n + 1)[idx - 1]


def _r2c(J, diag=False):
    n = J * (J + (1 if diag else -1)) // 2
    if n <= 0:
        return np.array([], dtype=int)
    cL = np.zeros((J, J), dtype=int)
    lt = _lt(J, diag=diag)
    ut = ~lt
    diagonal = np.diag(ut).copy()
    np.fill_diagonal(ut, np.logical_not(diagonal))
    _set_f(cL, ut, np.arange(1, n + 1))
    idx = cL.T.ravel(order="F")[lt.ravel(order="F")]
    return np.arange(1, n + 1)[idx - 1]


def _reorder(x, byrow=False):
    if bool(x.byrow) == bool(byrow):
        return x
    data = np.array(x, dtype=np.float64, copy=True, subok=False)
    if x.byrow:
        data = data[_r2c(x.J, x.diag) - 1, :]
        target = False
    else:
        data = data[_c2r(x.J, x.diag) - 1, :]
        target = True
    return ltMatrices(
        data,
        diag=x.diag,
        byrow=target,
        names=_names_arg(x),
        _colnames=x.colnames,
    )


class _Named(np.ndarray):
    """Numeric array that can carry R dimnames."""

    def __new__(cls, data):
        array = np.array(data, dtype=np.float64, copy=True, subok=False)
        return array.view(cls)

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.rownames = getattr(obj, "rownames", None)
        self.colnames = getattr(obj, "colnames", None)
        self.names = getattr(obj, "names", None)
        self.dimnames = getattr(obj, "dimnames", None)


def _attach_names(array, rownames=None, colnames=None):
    ret = _Named(array)
    ret.rownames = None if rownames is None else list(rownames)
    ret.colnames = None if colnames is None else list(colnames)
    return ret


def ltMatrices(object, diag=False, byrow=False, names=True, _colnames=None):
    if is_ltMatrices(object):
        ret = _reorder(object, byrow=byrow)
        if ret is not object:
            ret.rclass = list(object.rclass)
        return ret

    if not _is_matrix(object):
        flat = np.asarray(object, dtype=np.float64).ravel(order="F")
        data = flat.reshape((-1, 1))
        colnames = None
    else:
        data = np.array(object, dtype=np.float64, copy=True, subok=False)
        colnames = _colnames if _colnames is not None else getattr(object, "colnames", None)

    J = _infer_J(data.shape[0], bool(diag))
    nonames = False
    labels = names
    if not _is_true(names):
        if _is_character(names):
            labels = _as_character_vector(names)
            stopifnot(
                len(_unique(labels)) == J,
                "is.character(names) && length(unique(names)) == J",
            )
        else:
            nonames = True
    else:
        labels = [str(i) for i in range(1, J + 1)]

    rownames = None
    if not nonames:
        rownames = _element_names(J, bool(diag), bool(byrow), labels)
    else:
        warnings.warn("ltMatrices objects should be properly named", stacklevel=2)
        labels = names

    return LtMatrices(
        data,
        J,
        bool(diag),
        bool(byrow),
        labels if not nonames else names,
        ["ltMatrices", "matrix", "array"],
        rownames,
        None if colnames is None else list(colnames),
    )


def is_ltMatrices(x):
    return _has_class(x, "ltMatrices")


def is_syMatrices(x):
    return _has_class(x, "syMatrices")


def is_chol(x):
    return _has_class(x, "chol")


def is_invchol(x):
    return _has_class(x, "invchol")


def as_syMatrices(x):
    if is_syMatrices(x):
        return x
    if is_ltMatrices(x):
        ret = x.copy()
        ret.rclass = [item.replace("ltMatrices", "syMatrices") for item in ret.rclass]
        return ret
    array = np.asarray(x, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape((-1, 1))
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise LtError("non-conformable array")
    masked = np.where(_lt(array.shape[0], diag=True), array, 0.0)
    return as_syMatrices(as_ltMatrices(masked))


def syMatrices(object, diag=False, byrow=False, names=True):
    if is_syMatrices(object) and not is_ltMatrices(object):
        object = object.copy()
        object.rclass = [item.replace("syMatrices", "ltMatrices") for item in object.rclass]
    return as_syMatrices(ltMatrices(object, diag=diag, byrow=byrow, names=names))


def _as_lt_from_sy(x):
    ret = x.copy()
    start = ret.rclass.index("syMatrices")
    ret.rclass = ret.rclass[start:]
    ret.rclass[0] = "ltMatrices"
    return ret


def _as_lt_from_lt(x):
    ret = x.copy()
    start = ret.rclass.index("ltMatrices")
    ret.rclass = ret.rclass[start:]
    return ret


def _as_lt_default(x):
    stopifnot(_is_numeric(x), "is.numeric(x)")
    if not _is_matrix(x):
        flat = np.asarray(x, dtype=np.float64).ravel(order="F")
        array = flat.reshape((-1, 1))
    else:
        array = np.array(x, dtype=np.float64, copy=True, subok=False)
    if array.shape[0] != array.shape[1]:
        raise LtError("(subscript) logical subscript too long")
    n = array.shape[0]
    diagonal = np.diag(array) if n else np.array([])
    if diagonal.size == 0:
        use_diag = False
    else:
        use_diag = bool(np.max(np.abs(diagonal - 1.0)) > _EPS and n > 1)
    upper = _ut(n, diag=False)
    up = array.ravel(order="F")[upper.ravel(order="F")]
    if up.size and not (np.max(np.abs(up)) < _EPS):
        raise LtError("max(abs(up)) < .Machine$double.eps is not TRUE")
    lower = _lt(n, diag=use_diag)
    values = array.ravel(order="F")[lower.ravel(order="F")]
    rownames = getattr(x, "rownames", None)
    if rownames:
        return ltMatrices(values, diag=use_diag, names=list(rownames))
    return ltMatrices(values, diag=use_diag)


def as_ltMatrices(x):
    classes = _class_vector(x)
    for name in classes:
        if name == "syMatrices":
            return _as_lt_from_sy(x)
        if name == "ltMatrices":
            return _as_lt_from_lt(x)
    return _as_lt_default(x)


def dimnames(x):
    if isinstance(x, LtMatrices):
        return [x.colnames, x.rcnames, x.rcnames]
    return getattr(x, "dimnames", None)


def names(x):
    if isinstance(x, LtMatrices):
        return x.rownames
    return getattr(x, "names", None)


def _dense_stack(x, symmetric=False):
    J = x.J
    n = x.shape[1]
    out = np.zeros((J, J, n), dtype=np.float64)
    for index in range(n):
        dense = _to_dense(np.array(x)[:, index], J, x.diag, x.byrow)
        if symmetric:
            dense = _sym_from_lower(dense)
        out[:, :, index] = dense
    return out


def as_array(x, symmetric=False, **kwargs):
    if not isinstance(x, LtMatrices):
        return np.asarray(x)
    for name in x.rclass:
        if name == "syMatrices":
            symmetric = True
            break
        if name == "ltMatrices":
            break
    out = _Named(_dense_stack(x, symmetric=symmetric))
    if x.rcnames is not False and x.rcnames is not None:
        out.dimnames = [list(x.rcnames), list(x.rcnames), x.colnames]
    return out


def _print_lt(x, zero_print=".", **kwargs):
    print(_format_lt(x))
    return x


def _print_sy(x, **kwargs):
    print(as_array(x))
    return x


def _match(labels, names):
    if names is False or names is None:
        raise LtError("all(j %in% dimnames(x)[[2L]]) is not TRUE")
    table = list(names)
    out = []
    for label in labels:
        if label not in table:
            out.append(None)
        else:
            out.append(table.index(label) + 1)
    return out


def _char_labels(j):
    if isinstance(j, str):
        return [j]
    if isinstance(j, np.ndarray) and j.dtype.kind in "UOS":
        return [str(item) for item in j.tolist()]
    if isinstance(j, (list, tuple)) and j and isinstance(j[0], str):
        return list(j)
    return None


def _expand_index(j, n):
    """R's ``(1:n)[j]`` as 0-based positions."""
    values = np.atleast_1d(np.asarray(j, dtype=float)).ravel()
    if np.any(np.isnan(values)):
        raise LtError("NAs are not allowed in subscripted assignments")
    if np.any(values > 0) and np.any(values < 0):
        raise LtError("only 0's may be mixed with negative subscripts")
    if np.any(values < 0):
        excluded = set()
        for item in values:
            if item == 0:
                continue
            index = int(math.trunc(item))
            if index > 0 or -index > n:
                raise LtError("subscript out of bounds")
            excluded.add(-index)
        return np.array([i for i in range(n) if (i + 1) not in excluded], dtype=int)
    out = []
    for item in values:
        if item == 0:
            continue
        index = int(math.trunc(item))
        if index < 1 or index > n:
            raise LtError("subscript out of bounds")
        out.append(index - 1)
    return np.array(out, dtype=int)


def _fill_column_major(target, mask, values):
    return _set_f(target, mask, values)


def _subset_lt(x, i=None, j=None, drop=False, check_order=True, i_missing=False, j_missing=False):
    if drop:
        warnings.warn("argument drop is ignored", stacklevel=2)
    if i_missing and j_missing:
        return x
    diag = x.diag
    byrow = x.byrow
    J = x.J
    if not j_missing:
        labels = _char_labels(j)
        if labels is not None:
            if x.rcnames is False or x.rcnames is None or not all(item in list(x.rcnames) for item in labels):
                raise LtError("all(j %in% dimnames(x)[[2L]]) is not TRUE")
            j = _match(labels, x.rcnames)
        j_values = np.atleast_1d(np.asarray(j, dtype=float)).ravel()
        if check_order and j_values.size and np.all(j_values > 0):
            if j_values.size >= 2 and np.any(np.diff(j_values) < 0):
                raise LtError("invalid subset argument j")
        positions = _expand_index(j_values, J)
        if positions.size == 1 and not diag:
            data = np.ones((1, x.shape[1]), dtype=np.float64)
            chosen = [x.rcnames[positions[0]]] if x.rcnames not in (False, None) else x.rcnames
            return ltMatrices(data, diag=True, byrow=byrow, names=chosen, _colnames=x.colnames)
        index = np.zeros((J, J), dtype=float)
        upper = _ut(J, diag=diag)
        count = int(np.sum(upper))
        if byrow:
            _fill_column_major(index, upper, np.arange(1, count + 1))
        else:
            _fill_column_major(index, _lt(J, diag=diag), np.arange(1, count + 1))
        index = index + index.T
        np.fill_diagonal(index, np.diag(index) / 2.0)
        index = index[np.ix_(positions, positions)]
        mask = _ut(index.shape[0], diag=diag) if byrow else _lt(index.shape[0], diag=diag)
        selected = index.ravel(order="F")[mask.ravel(order="F")]
        rows = np.rint(selected).astype(int) - 1
        if i_missing:
            data = np.array(x, dtype=np.float64, copy=True, subok=False)[rows, :]
            colnames = x.colnames
        else:
            cols = _expand_index(i, x.shape[1])
            data = np.array(x, dtype=np.float64, copy=True, subok=False)[np.ix_(rows, cols)]
            colnames = None if x.colnames is None else [x.colnames[col] for col in cols]
        if x.rcnames in (False, None):
            chosen = x.rcnames
        else:
            chosen = [x.rcnames[pos] for pos in positions]
        return ltMatrices(data, diag=diag, byrow=byrow, names=chosen, _colnames=colnames)
    cols = _expand_index(i, x.shape[1])
    data = np.array(x, dtype=np.float64, copy=True, subok=False)[:, cols]
    colnames = None if x.colnames is None else [x.colnames[col] for col in cols]
    return ltMatrices(data, diag=diag, byrow=byrow, names=_names_arg(x), _colnames=colnames)


def bracket_lt(x, i=None, j=None, drop=False, **kwargs):
    return _subset_lt(
        x,
        i=i,
        j=j,
        drop=drop,
        check_order=True,
        i_missing=i is None and "i" not in kwargs,
        j_missing=j is None and "j" not in kwargs,
    )


def bracket_sy(x, i=None, j=None, drop=False, **kwargs):
    ret = _subset_lt(
        as_syMatrices(x) if not is_syMatrices(x) else x,
        i=i,
        j=j,
        drop=drop,
        check_order=False,
        i_missing=i is None and "i" not in kwargs,
        j_missing=j is None and "j" not in kwargs,
    )
    # ``as_syMatrices`` already ran inside subset via ltMatrices. Put sy first.
    if is_ltMatrices(ret):
        ret = as_syMatrices(ret)
    return ret


def _subset(x, i=None, j=None, i_missing=False, j_missing=False, check_order=None):
    if check_order is None:
        check_order = is_ltMatrices(x) and not (is_syMatrices(x) and not is_ltMatrices(x))
    if is_syMatrices(x) and not is_ltMatrices(x):
        check_order = False
    ret = _subset_lt(
        x,
        i=i,
        j=j,
        drop=False,
        check_order=check_order,
        i_missing=i_missing,
        j_missing=j_missing,
    )
    if is_syMatrices(x) and not is_ltMatrices(x):
        ret = as_syMatrices(ret)
    return ret


def Lower_tri(x, diag=False, byrow=None):
    if is_syMatrices(x) and not is_ltMatrices(x):
        x = as_ltMatrices(x)
    adiag = bool(diag)
    if byrow is None:
        byrow = bool(getattr(x, "byrow", False))
    x = ltMatrices(x, byrow=byrow)
    if bool(x.diag) == adiag:
        return np.array(x, dtype=np.float64, copy=True, subok=False)
    if (not x.diag) and adiag:
        x = set_diagonals(x, diagonals(x))
        return np.array(x, dtype=np.float64, copy=True, subok=False)
    J = x.J
    if J == 1:
        idx = np.array([0], dtype=int)
    elif x.byrow:
        idx = np.cumsum(np.concatenate([[1], np.arange(2, J + 1)])) - 1
    else:
        idx = np.cumsum(np.concatenate([[1], np.arange(J, 1, -1)])) - 1
    keep = np.ones(x.shape[0], dtype=bool)
    keep[idx] = False
    return np.array(x, dtype=np.float64, copy=True, subok=False)[keep, :]


def _diag_positions(J, byrow):
    if J <= 1:
        return np.array([0], dtype=int) if J == 1 else np.array([], dtype=int)
    if byrow:
        steps = np.concatenate([[1], np.arange(2, J + 1)])
    else:
        steps = np.concatenate([[1], np.arange(J, 1, -1)])
    return np.cumsum(steps).astype(int) - 1


def _diagonals_lt(x, **kwargs):
    J = x.J
    n = x.shape[1]
    if not x.diag:
        ret = np.ones((J, n), dtype=np.float64)
        return _attach_names(
            ret,
            None if x.rcnames in (False, None) else list(x.rcnames),
            x.colnames,
        )
    if J == 1:
        return x
    idx = _diag_positions(J, x.byrow)
    ret = np.array(x, dtype=np.float64, copy=True, subok=False)[idx, :]
    return _attach_names(ret, None if x.rcnames in (False, None) else list(x.rcnames), x.colnames)


def _diagonals_matrix(x, **kwargs):
    return np.diag(np.asarray(x, dtype=np.float64))


def _diagonals_integer(x, **kwargs):
    number = int(x)
    return ltMatrices(np.zeros(number * (number - 1) // 2, dtype=np.float64), diag=False, **kwargs)


def diagonals(x, **kwargs):
    for name in _class_vector(x):
        if name in ("syMatrices", "ltMatrices"):
            return _diagonals_lt(x)
        if name == "matrix":
            return _diagonals_matrix(x)
        if name == "integer":
            return _diagonals_integer(x, **kwargs)
    raise LtError("no applicable method for 'diagonals'")


def _adddiag(x):
    if x.diag:
        return x
    if is_syMatrices(x) and not is_ltMatrices(x):
        # R still dispatches dim() as syMatrices while ltMatrices() assigns rownames.
        raise LtError("length of 'dimnames' [3] must match that of 'dims' [2]")
    byrow_orig = x.byrow
    ordered = ltMatrices(x, byrow=False)
    n = ordered.shape[1]
    J = ordered.J
    labels = _names_arg(ordered)
    total = J * (J + 1) // 2
    lower = _lt(J, diag=True)
    positions = np.zeros((J, J), dtype=int)
    _set_f(positions, lower, np.arange(1, total + 1))
    ret = np.zeros((total, n), dtype=np.float64)
    rows, cols = _tri_index(J, True, False)
    for row, col, slot in zip(rows, cols, positions[rows, cols]):
        if row == col:
            ret[slot - 1, :] = 1.0
    strict = _lt(J, diag=False)
    src = np.array(ordered, dtype=np.float64, copy=False, subok=False)
    ret[positions.ravel(order="F")[strict.ravel(order="F")] - 1, :] = src
    built = ltMatrices(ret, diag=True, byrow=False, names=labels, _colnames=ordered.colnames)
    return ltMatrices(built, byrow=byrow_orig)


def _set_diag_lt(x, value):
    J = x.J
    n = x.shape[1]
    byrow = x.byrow
    if value is None:
        if not x.diag:
            return x
        if J == 1:
            ret = x.copy()
            ret[...] = 1
            return ret
        idx = _diag_positions(J, byrow)
        keep = np.ones(x.shape[0], dtype=bool)
        keep[idx] = False
        data = np.array(x, dtype=np.float64, copy=True, subok=False)[keep, :]
        return ltMatrices(data, diag=False, byrow=byrow, names=_names_arg(x), _colnames=x.colnames)
    y = _adddiag(x)
    if not _is_matrix(value):
        value = _r_matrix(value, J, y.shape[1])
    else:
        value = np.array(value, dtype=np.float64, copy=True, subok=False)
    stopifnot(
        _is_matrix(value) and value.shape[0] == J and value.shape[1] == y.shape[1],
        "is.matrix(value) && nrow(value) == J && ncol(value) == d[1L]",
    )
    y = y.copy()
    if J == 1:
        y[...] = value
        return y
    y[_diag_positions(J, y.byrow), :] = value
    return y


def _set_diag_sy(x, value):
    y = as_ltMatrices(x)
    y = _set_diag_lt(y, value)
    y.rclass[0] = "syMatrices"
    return y


def set_diagonals(x, value):
    for name in _class_vector(x):
        if name == "syMatrices":
            return _set_diag_sy(x, value)
        if name == "ltMatrices":
            return _set_diag_lt(x, value)
    raise LtError("no applicable method for 'diagonals<-'")


def _cholesky_lower(matrix):
    size = matrix.shape[0]
    try:
        return np.linalg.cholesky(np.asarray(matrix, dtype=np.float64))
    except np.linalg.LinAlgError:
        for order in range(1, size + 1):
            try:
                np.linalg.cholesky(np.asarray(matrix[:order, :order], dtype=np.float64))
            except np.linalg.LinAlgError:
                raise LtError(
                    f"the leading minor of order {order} is not positive definite"
                ) from None
        raise LtError("the leading minor of order 1 is not positive definite")


def _solve_lower(lower, rhs, transpose=False):
    size = lower.shape[0]
    x = np.array(rhs, dtype=np.float64, copy=True)
    if x.ndim == 1:
        x = x.reshape((-1, 1))
        squeeze = True
    else:
        squeeze = False
    if not transpose:
        for i in range(size):
            if i:
                x[i, :] -= lower[i, :i] @ x[:i, :]
            diag = lower[i, i]
            if diag == 0.0:
                raise LtError("Cannot solve ltMatrices")
            x[i, :] /= diag
    else:
        for i in range(size - 1, -1, -1):
            if i + 1 < size:
                x[i, :] -= lower[i + 1 :, i] @ x[i + 1 :, :]
            diag = lower[i, i]
            if diag == 0.0:
                raise LtError("Cannot solve ltMatrices")
            x[i, :] /= diag
    if squeeze:
        return x.reshape(-1)
    return x


def _invert_lower(lower):
    size = lower.shape[0]
    eye = np.eye(size, dtype=np.float64)
    out = np.zeros((size, size), dtype=np.float64)
    for col in range(size):
        out[:, col] = _solve_lower(lower, eye[:, col], transpose=False)
    return out


def _matrices(x):
    return [_to_dense(np.array(x)[:, index], x.J, x.diag, x.byrow) for index in range(x.shape[1])]


def _replace_packed(template, columns, diag, byrow):
    data = np.column_stack(columns) if columns else np.zeros((0, template.shape[1]))
    if data.ndim == 1:
        data = data.reshape((-1, 1))
    return LtMatrices(
        data,
        template.J,
        diag,
        byrow,
        template.rcnames,
        template.rclass,
        _element_names(template.J, diag, byrow, template.rcnames)
        if template.rcnames not in (False, None)
        else None,
        template.colnames,
    )


def _mult_lt(x, y=None, transpose=False):
    use_diag = bool(x.diag)
    work = x if use_diag else set_diagonals(x, diagonals(x))
    J = work.J
    n_mat = x.shape[1]
    byrow = work.byrow
    if y is None:
        stopifnot(not byrow, "!byrow")
        stopifnot(bool(transpose), "transpose")
        y = Lower_tri(work, diag=True)
    else:
        stopifnot(_nrow(y) == J or _nrow(y) == J * J, "NROW(y) == J || NROW(y) == J^2")
    stopifnot(_is_numeric(y), "is.numeric(y)")
    if not _is_matrix(y):
        y = _r_matrix(y, J, n_mat)
    else:
        y = np.array(y, dtype=np.float64, copy=True, subok=False)
    n = y.shape[1] if n_mat == 1 else n_mat
    if y.shape[1] != n:
        # R drops each column to a vector. The next call recycles it across N.
        pieces = []
        for index in range(y.shape[1]):
            piece = np.asarray(_mult_lt(x, y[:, index], transpose=transpose), dtype=np.float64)
            pieces.append(piece.ravel(order="F"))
        return np.column_stack(pieces)
    factors = _matrices(work)
    if n_mat == 1:
        factors = factors * n
    y_size = y.size
    if y_size == J * n:
        mode = 1
    elif y_size == J * J * n:
        mode = 2
    elif y_size == J * (J + 1) // 2 * n:
        if not (transpose and not byrow):
            raise LtError("matrix multiplication not implemented")
        mode = 3
    else:
        raise LtError("incorrect dimension of y argument")
    out_cols = []
    for index in range(n):
        factor = factors[index]
        if mode == 1:
            vec = y[:, index]
            out_cols.append(_solve_or_mult(factor, vec, transpose))
        elif mode == 2:
            block = y[:, index].reshape((J, J), order="F")
            prod = factor.T @ block if transpose else factor @ block
            out_cols.append(prod.ravel(order="F"))
        else:
            dense_m = _to_dense(y[:, index], J, True, False)
            prod = factor.T @ dense_m
            out_cols.append(_pack(prod, True, False))
    ret = np.column_stack(out_cols)
    if ret.ndim == 1:
        ret = ret.reshape((-1, 1))
    dn = dimnames(x)
    rownames = list(dn[1]) if mode == 1 and dn[1] not in (False, None) else None
    colnames = list(dn[0]) if dn[0] not in (None, False) and len(dn[0]) == n else None
    return _attach_names(ret, rownames, colnames)


def _solve_or_mult(factor, vec, transpose):
    if transpose:
        return factor.T @ vec
    return factor @ vec


def _mult_sy(x, y):
    if y is None:
        raise LtError('argument "y" is missing, with no default')
    stopifnot(_is_numeric(y), "is.numeric(y)")
    J = x.J
    n_mat = x.shape[1]
    if not _is_matrix(y):
        y = _r_matrix(y, J, n_mat)
    else:
        y = np.array(y, dtype=np.float64, copy=True, subok=False)
    n = y.shape[1] if n_mat == 1 else n_mat
    stopifnot(y.shape[0] == J, "nrow(y) == d[2L]")
    stopifnot(y.shape[1] == n, "ncol(y) == N")
    base = as_ltMatrices(x)
    diag_mat = np.asarray(diagonals(x), dtype=np.float64)
    if diag_mat.ndim == 1:
        diag_mat = diag_mat.reshape((-1, 1))
    product = y * diag_mat
    return _mult_lt(base, y, transpose=False) + _mult_lt(base, y, transpose=True) - product


def _mult_default(x, y=None, transpose=False):
    array = np.asarray(x, dtype=np.float64)
    if not transpose:
        if y is None:
            raise LtError("requires numeric/complex matrix/vector arguments")
        return array @ np.asarray(y, dtype=np.float64)
    return array.T @ array


def Mult(x, y=None, transpose=False, **kwargs):
    classes = _class_vector(x)
    for name in classes:
        if name == "syMatrices":
            if y is None:
                raise LtError('argument "y" is missing, with no default')
            return _mult_sy(x, y)
        if name == "ltMatrices":
            return _mult_lt(x, y, transpose=transpose)
    return _mult_default(x, y, transpose)


def _solve_lt(a, b=None, transpose=False, b_missing=False):
    orig_diag = bool(a.diag)
    work = a if orig_diag else set_diagonals(a, diagonals(a))
    J = work.J
    if not b_missing:
        stopifnot(_is_numeric(b) if not _is_matrix(b) else True, "is.numeric(b)")
        if not _is_matrix(b):
            b = _r_matrix(b, J, a.shape[1])
        else:
            b = np.array(b, dtype=np.float64, copy=True, subok=False)
        stopifnot(b.shape[0] == J, "nrow(b) == J")
        n = b.shape[1] if a.shape[1] == 1 else a.shape[1]
        stopifnot(b.shape[1] == n, "ncol(b) == N")
        factors = _matrices(work)
        if a.shape[1] == 1:
            factors = factors * n
        cols = []
        for index in range(n):
            cols.append(_solve_lower(factors[index], b[:, index], transpose=transpose))
        ret = np.column_stack(cols)
        dn = dimnames(a)
        rownames = dn[1] if dn[1] not in (False, None) else None
        if a.shape[1] == n:
            colnames = dn[0]
        else:
            colnames = getattr(b, "colnames", None)
        return _attach_names(ret, rownames, colnames)
    if transpose:
        raise LtError("cannot compute inverse of t(a)")
    factors = _matrices(work)
    packed = [_pack(_invert_lower(factor), True, work.byrow) for factor in factors]
    ret = _replace_packed(work, packed, True, work.byrow)
    ret.rclass = list(work.rclass)
    if is_chol(ret):
        ret.rclass = [item.replace("chol", "invchol") for item in ret.rclass]
    elif is_invchol(ret):
        ret.rclass = [item.replace("invchol", "chol") for item in ret.rclass]
    if orig_diag:
        return ret
    return ltMatrices(Lower_tri(ret, diag=False), byrow=a.byrow, names=_names_arg(a))


def solve(a, b=None, transpose=False, **kwargs):
    b_missing = b is None and "b" not in kwargs
    # ``b=None`` is the missing right-hand side. A caller that needs the
    # inverse omits b. Passing a matrix selects the system solver.
    if not isinstance(a, LtMatrices):
        matrix = np.asarray(a, dtype=np.float64)
        if b is None:
            return np.linalg.inv(matrix)
        return np.linalg.solve(matrix, np.asarray(b, dtype=np.float64))
    for name in a.rclass:
        if name == "ltMatrices":
            return _solve_lt(a, b, transpose=transpose, b_missing=b_missing)
    return _solve_lt(a, b, transpose=transpose, b_missing=b_missing)


def logdet(x):
    if not is_ltMatrices(x):
        raise LtError("x is not an ltMatrices object")
    n = x.shape[1]
    out = np.zeros(n, dtype=np.float64)
    if x.diag:
        idx = _diag_positions(x.J, x.byrow)
        data = np.array(x, dtype=np.float64, copy=False, subok=False)
        for index in range(n):
            out[index] = np.sum(np.log(data[idx, index]))
    out = _Named(out)
    if x.colnames is not None:
        out.names = list(x.colnames)
    return out


def _squared(x):
    ret = x.copy()
    ret[...] = np.array(x, dtype=np.float64, copy=False, subok=False) ** 2
    return ret


def _margin_sums(x, columns):
    array = as_array(_squared(x))
    reduced = array.sum(axis=0) if columns else array.sum(axis=1)
    if reduced.ndim == 1:
        reduced = reduced.reshape((-1, 1))
    labels = None if x.rcnames in (False, None) else list(x.rcnames)
    return _attach_names(reduced, labels, x.colnames)


def _Tcrossprod(x, diag_only=False, transpose=False):
    if not is_ltMatrices(x):
        x = as_ltMatrices(x)
    if transpose:
        if diag_only:
            return _margin_sums(x, columns=True)
        byrow_orig = x.byrow
        ordered = ltMatrices(x, byrow=False)
        packed = Mult(ordered, transpose=True)
        ret = syMatrices(packed, diag=True, byrow=False, names=_names_arg(ordered))
        return syMatrices(ret, byrow=byrow_orig)
    if diag_only:
        return _margin_sums(x, columns=False)
    byrow_orig = x.byrow
    array = as_array(x)
    ax = np.transpose(array, (1, 0, 2)).reshape((x.J * x.J, x.shape[1]), order="F")
    ordered = ltMatrices(x, byrow=False)
    prod = Mult(ordered, ax, transpose=False)
    rows, cols = _tri_index(x.J, True, False)
    slots = (cols * x.J + rows).astype(int)
    packed = prod[slots, :]
    ret = syMatrices(packed, diag=True, byrow=False, names=_names_arg(ordered))
    return syMatrices(ret, byrow=byrow_orig)


def Tcrossprod(x, diag_only=False):
    return _Tcrossprod(x, diag_only=diag_only, transpose=False)


def Crossprod(x, diag_only=False):
    return _Tcrossprod(x, diag_only=diag_only, transpose=True)


def crossprod(x, y=None, **kwargs):
    if is_ltMatrices(x) or (is_syMatrices(x) and not is_ltMatrices(x)):
        if y is None:
            return Crossprod(x, **kwargs)
        return Mult(x, y, transpose=True)
    array = np.asarray(x, dtype=np.float64)
    if y is None:
        return array.T @ array
    return array.T @ np.asarray(y, dtype=np.float64)


def tcrossprod(x, y=None, **kwargs):
    if is_ltMatrices(x) or (is_syMatrices(x) and not is_ltMatrices(x)):
        if y is None:
            return Tcrossprod(x, **kwargs)
        return Mult(x, y, transpose=False)
    array = np.asarray(x, dtype=np.float64)
    if y is None:
        return array @ array.T
    return array @ np.asarray(y, dtype=np.float64).T


def _chol_sy(x):
    work = _adddiag(x)
    out = work.copy()
    for index in range(out.shape[1]):
        dense = _to_dense(np.array(out)[:, index], out.J, True, out.byrow)
        factor = _cholesky_lower(_sym_from_lower(dense))
        out[:, index] = _pack(factor, True, out.byrow)
    out.rclass = [item.replace("syMatrices", "ltMatrices") for item in out.rclass]
    if out.rcnames not in (False, None):
        out.rownames = _element_names(out.J, True, out.byrow, out.rcnames)
    return out


def chol(x, **kwargs):
    if is_syMatrices(x):
        return _chol_sy(x)
    matrix = np.asarray(x, dtype=np.float64)
    return _cholesky_lower(_sym_from_lower(matrix) if matrix.shape[0] == matrix.shape[1] else matrix).T


def _c_invchol(J, ans):
    """In-place inverse Cholesky on a row-major packed triangle."""
    eps = _EPS
    if ans[0] < eps:
        return 1
    ans[0] = 1.0 / math.sqrt(ans[0])
    start = 1
    end = 0
    for j in range(1, J):
        sd = 0.0
        for i in range(j - 1, -1, -1):
            ans[start + i] *= ans[end]
            for k in range(1, i + 1):
                ans[start + i] += ans[end - k] * ans[start + i - k]
            sd += ans[start + i] ** 2
            end -= i + 1
        sd = ans[start + j] - sd
        if sd < eps:
            return j
        sd = math.sqrt(sd)
        str_ = 0
        for i in range(j):
            x = str_ + i
            ans[start + i] *= ans[x]
            for k in range(i + 1, j):
                x += k
                ans[start + i] += ans[x] * ans[start + k]
            str_ += i + 1
        for i in range(j):
            ans[start + i] = -ans[start + i] / sd
        ans[start + j] = 1.0 / sd
        start += j + 1
        end = start - 1
    return 0


def _invchol_sy(x):
    byrow_orig = x.byrow
    work = _adddiag(x).copy()
    work.rclass = [item.replace("syMatrices", "ltMatrices") for item in work.rclass]
    work = ltMatrices(work, byrow=True)
    data = np.array(work, dtype=np.float64, copy=True, subok=False)
    for index in range(data.shape[1]):
        column = np.array(data[:, index], dtype=np.float64, copy=True)
        info = _c_invchol(work.J, column)
        if info != 0:
            raise LtError(f"the leading minor of order {info} is not positive definite")
        data[:, index] = column
    ret = LtMatrices(
        data,
        work.J,
        True,
        True,
        work.rcnames,
        work.rclass,
        _element_names(work.J, True, True, work.rcnames) if work.rcnames not in (False, None) else None,
        work.colnames,
    )
    return ltMatrices(ret, byrow=byrow_orig)


def _as_matrix(x):
    if isinstance(x, LtMatrices):
        return np.array(x, dtype=np.float64, copy=True, subok=False)
    array = np.asarray(x, dtype=np.float64)
    if array.ndim <= 1:
        return array.reshape((-1, 1))
    return np.array(array, dtype=np.float64, copy=True)


def invchol(x, **kwargs):
    if is_syMatrices(x) and not is_ltMatrices(x):
        return _invchol_sy(x)
    if is_syMatrices(x):
        return _invchol_sy(x)
    return invchol(as_syMatrices(_as_matrix(x)))


def _clamp_D(D):
    D = np.array(D, dtype=np.float64, copy=True)
    D[D < _EPS] = 2 * _EPS
    D[D > 1.0 / _EPS] = (1.0 / _EPS) / 2.0
    return D


def _d_index(J, byrow, rows=True):
    if rows:
        if byrow:
            return np.repeat(np.arange(1, J + 1), np.arange(1, J + 1))
        idx = []
        for j in range(1, J + 1):
            idx.extend(range(j, J + 1))
        return np.asarray(idx, dtype=int)
    if byrow:
        idx = []
        for j in range(1, J + 1):
            idx.extend(range(1, j + 1))
        return np.asarray(idx, dtype=int)
    return np.repeat(np.arange(1, J + 1), np.arange(J, 0, -1))


def Dchol(x, D=None):
    if is_invchol(x):
        raise LtError("Dchol cannot work with invchol objects")
    if D is None:
        D = 1.0 / np.sqrt(Tcrossprod(x, diag_only=True))
    x = _adddiag(x).copy()
    D = _clamp_D(D)
    if D.ndim == 1:
        D = D.reshape((-1, 1))
    idx = _d_index(x.J, x.byrow, rows=True)
    x[...] = np.array(x, dtype=np.float64, copy=False, subok=False) * D[idx - 1, :]
    return as_chol(x)


def invcholD(x, D=None):
    if is_chol(x):
        raise LtError("invcholD cannot work with chol objects")
    if D is None:
        D = np.sqrt(Tcrossprod(solve(x), diag_only=True))
    x = _adddiag(x).copy()
    D = _clamp_D(D)
    if D.ndim == 1:
        D = D.reshape((-1, 1))
    idx = _d_index(x.J, x.byrow, rows=False)
    x[...] = np.array(x, dtype=np.float64, copy=False, subok=False) * D[idx - 1, :]
    return as_invchol(x)


def as_chol(x):
    stopifnot(is_ltMatrices(x), "is.ltMatrices(x)")
    if is_chol(x):
        return x
    if is_invchol(x):
        return invchol2chol(x)
    ret = x.copy()
    ret.rclass = ["chol"] + list(ret.rclass)
    return ret


def as_invchol(x):
    stopifnot(is_ltMatrices(x), "is.ltMatrices(x)")
    if is_invchol(x):
        return x
    if is_chol(x):
        return chol2invchol(x)
    ret = x.copy()
    ret.rclass = ["invchol"] + list(ret.rclass)
    return ret


def chol2cov(x):
    return Tcrossprod(x)


def cov2chol(x):
    return as_chol(chol(x))


def invchol2chol(x):
    return as_chol(solve(x))


def chol2invchol(x):
    return as_invchol(solve(x))


def invchol2cov(x):
    return chol2cov(invchol2chol(x))


def cov2invchol(x):
    return as_invchol(invchol(x))


def invchol2pre(x):
    return Crossprod(x)


def chol2pre(x):
    return Crossprod(chol2invchol(x))


def chol2cor(x):
    ret = Tcrossprod(Dchol(x))
    return set_diagonals(ret, None)


def invchol2cor(x):
    ret = chol2cor(invchol2chol(x))
    return set_diagonals(ret, None)


def invchol2pc(x):
    scale = 1.0 / np.sqrt(Crossprod(x, diag_only=True))
    ret = -Crossprod(invcholD(x, D=scale))
    return set_diagonals(ret, 0)


def chol2pc(x):
    return invchol2pc(solve(x))


def _vec_transpose_index(J):
    order = np.arange(1, J * J + 1).reshape((J, J), order="F")
    return order.T.ravel(order="F")


def vectrick(C, S=None, A=None, transpose=(True, True), _S_missing=False, _A_missing=False):
    # None means missing when the caller omits S or A. An explicit matrix is not None.
    if isinstance(transpose, bool) or (isinstance(transpose, np.ndarray) and transpose.ndim == 0):
        logical = [bool(transpose)]
    else:
        logical = [bool(item) for item in np.atleast_1d(np.asarray(transpose)).ravel()]
        if not all(isinstance(item, (bool, np.bool_)) for item in np.atleast_1d(transpose).ravel()):
            if np.asarray(transpose).dtype.kind not in "b":
                raise LtError("all(is.logical(transpose)) is not TRUE")
    stopifnot(len(logical) == 2, "length(transpose) == 2L")
    s_missing = S is None
    a_missing = A is None
    if s_missing and a_missing:
        if logical[0] and not logical[1]:
            return crossprod(C)
        if (not logical[0]) and logical[1]:
            return tcrossprod(C)
    C = as_ltMatrices(C)
    J = C.J
    N = C.shape[1]
    nm = C.rcnames
    if s_missing:
        sltm = True
        CS = as_array(C)
        if logical[0]:
            CS = np.transpose(CS, (1, 0, 2))
        CS = np.ascontiguousarray(CS).reshape((J * J, CS.shape[2]), order="F")
    else:
        sltm = is_ltMatrices(S)
        if sltm or is_syMatrices(S):
            if bool(S.byrow) != bool(C.byrow):
                raise LtError("S_byrow_orig == C_byrow_orig is not TRUE")
            stopifnot(C.J == S.J, "dC[2L] == dS[2L]")
            if C.shape[1] != 1:
                stopifnot(C.shape[1] == S.shape[1], "dC[1L] == dS[1L]")
            else:
                N = S.shape[1]
            arr = as_array(S)
            S = np.array(arr, dtype=np.float64, copy=False).reshape((J * J, arr.shape[2]), order="F")
        else:
            stopifnot(_is_matrix(S), "is.matrix(S)")
            S = np.array(S, dtype=np.float64, copy=True, subok=False)
            stopifnot(S.shape[0] == J * J, "nrow(S) == J^2")
            if C.shape[1] != 1:
                stopifnot(C.shape[1] == S.shape[1], "dC[1L] == ncol(S)")
            else:
                N = S.shape[1]
        CS = Mult(C, S, transpose=logical[0])
    if a_missing:
        A = C
    else:
        A = as_ltMatrices(A)
        if bool(C.byrow) != bool(A.byrow):
            raise LtError("C_byrow_orig == A_byrow_orig is not TRUE")
        stopifnot(C.J == A.J, "dC[2L] == dA[2L]")
    TR = _vec_transpose_index(J)
    CS = np.asarray(CS, dtype=np.float64)[TR - 1, :]
    ret = np.asarray(Mult(A, CS, transpose=not logical[1]), dtype=np.float64)[TR - 1, :]
    if not sltm:
        return np.array(ret, dtype=np.float64, copy=True).reshape((-1, N), order="F")
    slots = np.arange(J * J).reshape((J, J), order="F")
    mask = _lt(J, diag=True)
    chosen = slots.ravel(order="F")[mask.ravel(order="F")]
    packed = ltMatrices(ret[chosen, :], diag=True, byrow=False, names=nm)
    return ltMatrices(packed, byrow=C.byrow)


def _coerce_which(which, x):
    labels = _char_labels(which)
    if labels is not None:
        matched = _match(labels, dimnames(x)[1])
        if any(item is None for item in matched):
            raise LtError("all(which %in% 1:J) is not TRUE")
        which = matched
    which = np.atleast_1d(np.asarray(which, dtype=int)).ravel()
    J = x.J
    stopifnot(bool(np.all(np.isin(which, np.arange(1, J + 1)))), "all(which %in% 1:J)")
    return which


def marg_mvnorm(chol=None, invchol=None, which=None, _which_missing=False):
    # Detect a missing ``which`` by a private flag so ``which=1`` still subsets.
    chol_missing = chol is None
    inv_missing = invchol is None
    stopifnot(chol_missing ^ inv_missing, "xor(missing(chol), missing(invchol))")
    x = invchol if chol_missing else chol
    stopifnot(is_ltMatrices(x), "is.ltMatrices(x)")
    if which is None and not _which_supplied(marg_mvnorm, which):
        return x
    # The default call omits which. Callers that subset pass it.
    if which is None:
        return x
    which = _coerce_which(which, x)
    simple = which.size >= 1 and which[0] == 1 and (which.size == 1 or np.all(np.diff(which) == 1))
    if simple:
        tmp = _subset(x, j=which, j_missing=False, i_missing=True)
    elif chol_missing:
        tmp = cov2invchol(_subset(invchol2cov(x), j=which, j_missing=False, i_missing=True))
    else:
        tmp = cov2chol(_subset(chol2cov(x), j=which, j_missing=False, i_missing=True))
    if chol_missing:
        return {"invchol": tmp}
    return {"chol": tmp}


def _which_supplied(func, which):
    return False


def _cond_simple(x, which, given, center, from_chol):
    J = x.J
    L = solve(x) if from_chol else x
    tmp = np.zeros((J - which.size, given.shape[1]), dtype=np.float64)
    stacked = np.vstack([np.asarray(given, dtype=np.float64), tmp])
    centerm = np.asarray(Mult(L, stacked), dtype=np.float64)
    nL = L.shape[1]
    N = x.shape[1]
    if N == 1:
        N = given.shape[1]
    if nL > 1 and given.shape[1] != N:
        pieces = []
        for col in range(centerm.shape[1]):
            mat = _r_matrix(centerm[:, col], J, nL)
            keep = np.ones(J, dtype=bool)
            keep[which - 1] = False
            pieces.append(mat[keep, :])
        centerm_matrix = False
    else:
        keep = np.ones(centerm.shape[0], dtype=bool)
        keep[which - 1] = False
        centerm = centerm[keep, :]
        pieces = None
        centerm_matrix = True
    L2 = _subset(L, j=-which, j_missing=False, i_missing=True)
    if centerm_matrix:
        ct = centerm
        mean = -np.asarray(solve(L2, centerm), dtype=np.float64)
    else:
        ct = np.vstack(pieces)
        mean = np.vstack([-np.asarray(solve(L2, piece), dtype=np.float64) for piece in pieces])
    if from_chol:
        if center:
            return {"center": ct, "chol": solve(L2)}
        return {"mean": mean, "chol": solve(L2)}
    if center:
        return {"center": ct, "invchol": L2}
    return {"mean": mean, "invchol": L2}


def cond_mvnorm(chol=None, invchol=None, which_given=1, given=None, center=False):
    which = which_given
    chol_missing = chol is None
    inv_missing = invchol is None
    stopifnot(chol_missing ^ inv_missing, "xor(missing(chol), missing(invchol))")
    x = invchol if chol_missing else chol
    stopifnot(is_ltMatrices(x), "is.ltMatrices(x)")
    # ``which <- which_given`` forces the default, so missing(which) is never true.
    if given is None:
        raise LtError('argument "given" is missing, with no default')
    which = _coerce_which(which, x)
    N = x.shape[1]
    J = x.J
    if N == 1:
        N = _ncol(given)
    given = np.asarray(given, dtype=np.float64)
    stopifnot(_is_matrix(given) and given.shape[0] == which.size, "is.matrix(given) && nrow(given) == length(which)")
    simple = which[0] == 1 and (which.size == 1 or bool(np.all(np.diff(which) == 1)))
    if simple:
        return _cond_simple(x, which, given, center, from_chol=not chol_missing)
    if center:
        rest = [i for i in range(1, J + 1) if i not in set(int(v) for v in which)]
        perm = list(int(v) for v in which) + rest
        if not chol_missing:
            return cond_mvnorm(
                chol=aperm(as_chol(chol), perm=perm),
                which_given=list(range(1, which.size + 1)),
                given=given,
                center=center,
            )
        return cond_mvnorm(
            invchol=aperm(as_invchol(invchol), perm=perm),
            which_given=list(range(1, which.size + 1)),
            given=given,
            center=center,
        )
    if not chol_missing:
        P = Crossprod(solve(chol))
    else:
        P = Crossprod(invchol)
    Pw = _subset(P, j=-which, j_missing=False, i_missing=True)
    # The arguments shadow these names. R looks up the functions anyway.
    factor = globals()["invchol"](Pw)
    g0 = np.zeros((J, given.shape[1]), dtype=np.float64)
    g0[which - 1, :] = given
    S = Crossprod(factor)
    keep = np.ones(J, dtype=bool)
    keep[which - 1] = False
    if given.shape[1] in (1, N):
        Pg = np.asarray(Mult(P, g0), dtype=np.float64)[keep, :]
        mean = -np.asarray(Mult(S, Pg), dtype=np.float64)
    else:
        columns = []
        for index in range(given.shape[1]):
            Pi = np.asarray(Mult(P, g0[:, [index]]), dtype=np.float64)[keep, :]
            columns.append(-np.asarray(Mult(S, Pi), dtype=np.float64).ravel())
        mean = np.vstack(columns)
    if chol_missing:
        return {"mean": mean, "invchol": globals()["invchol"](S)}
    return {"mean": mean, "chol": globals()["chol"](S)}


def _aperm_perm(a, perm, extra):
    J = a.J
    if perm is None:
        return a
    labels = _char_labels(perm)
    if labels is not None:
        perm = _match(labels, dimnames(a)[1])
        if any(item is None for item in perm):
            raise LtError("all(perm %in% 1:J) is not TRUE")
    perm = np.atleast_1d(np.asarray(perm, dtype=int)).ravel()
    stopifnot(bool(np.all(np.isin(perm, np.arange(1, J + 1)))), "all(perm %in% 1:J)")
    if extra:
        warnings.warn("Additional arguments" + "".join(map(str, extra)) + "ignored", stacklevel=2)
    return perm


def _aperm_chol(a, perm=None, **kwargs):
    if perm is None:
        return a
    perm = _aperm_perm(a, perm, kwargs)
    return as_chol(chol(_subset(chol2cov(a), j=perm, j_missing=False, i_missing=True)))


def _aperm_invchol(a, perm=None, **kwargs):
    if perm is None:
        return a
    perm = _aperm_perm(a, perm, kwargs)
    return as_invchol(invchol(_subset(invchol2cov(a), j=perm, j_missing=False, i_missing=True)))


def _aperm_lt(a, perm=None, **kwargs):
    raise LtError(
        "Cannot permute objects of class ltMatrices, \n"
        "          consider calling as.chol() or as.invchol() first"
    )


def _aperm_sy(a, perm=None, **kwargs):
    if perm is None:
        return a
    return _subset(a, j=perm, j_missing=False, i_missing=True)


def aperm(a, perm=None, **kwargs):
    if isinstance(a, LtMatrices):
        for name in a.rclass:
            if name == "chol":
                return _aperm_chol(a, perm, **kwargs)
            if name == "invchol":
                return _aperm_invchol(a, perm, **kwargs)
            if name == "ltMatrices":
                return _aperm_lt(a, perm, **kwargs)
            if name == "syMatrices":
                return _aperm_sy(a, perm, **kwargs)
    raise LtError("no applicable method for 'aperm'")


def _unique_is_zero(mean):
    flat = np.asarray(mean, dtype=np.float64).ravel(order="F")
    if flat.size == 0 or not np.all(flat == flat[0]) or np.isnan(flat[0]):
        return False
    if flat[0] == 0.0 and np.signbit(flat[0]):
        return False
    return bool(flat[0] == 0.0)


def _check_obs_mean(obs, mean, J, N):
    obs = np.asarray(obs, dtype=np.float64)
    if obs.ndim == 1:
        obs = obs.reshape((-1, 1))
    if obs.shape[1] != N or obs.shape[0] != J:
        raise LtError("obs and (inv)chol have non-conforming size")
    if _unique_is_zero(mean):
        return obs
    flat = np.asarray(mean, dtype=np.float64).ravel(order="F")
    if flat.size == J:
        return obs - flat.reshape((J, 1))
    if np.asarray(mean).ndim != 2:
        raise LtError("obs and mean have non-conforming size")
    mean = np.asarray(mean, dtype=np.float64)
    if mean.shape[0] != obs.shape[0]:
        raise LtError("obs and mean have non-conforming size")
    if mean.shape[1] != obs.shape[1]:
        raise LtError("obs and mean have non-conforming size")
    return obs - mean


def _check_obs_invcholmean(obs, invcholmean, J, N):
    obs = np.asarray(obs, dtype=np.float64)
    if obs.ndim == 1:
        obs = obs.reshape((-1, 1))
    if obs.shape[1] != N or obs.shape[0] != J:
        raise LtError("obs and (inv)chol have non-conforming size")
    if invcholmean is None or _unique_is_zero(invcholmean):
        return np.zeros((J, N), dtype=np.float64)
    if not _is_matrix(invcholmean):
        invcholmean = _r_matrix(invcholmean, J, 1)
    else:
        invcholmean = np.array(invcholmean, dtype=np.float64, copy=True)
    if invcholmean.shape[1] not in (1, N):
        raise LtError("obs and (inv)chol have non-conforming size")
    if invcholmean.shape[0] != J:
        raise LtError("invcholmean and (inv)chol have non-conforming size")
    if invcholmean.shape[1] == N:
        return invcholmean
    return np.repeat(invcholmean, N, axis=1)


def _colSumsdnorm(z):
    stopifnot(_is_numeric(z), "is.numeric(z)")
    array = np.asarray(z, dtype=np.float64)
    if array.ndim == 1:
        array = array.reshape((1, -1))
    n = array.shape[1]
    rows = array.shape[0]
    scale = rows * math.log(2.0 * math.pi)
    out = np.empty(n, dtype=np.float64)
    for index in range(n):
        out[index] = -0.5 * (scale + np.sum(array[:, index] ** 2))
    out = _Named(out)
    colnames = getattr(z, "colnames", None)
    if colnames is not None:
        out.names = list(colnames)
    return out


# R names, including dotted helpers and replacement functions.
globals()[".lt"] = _lt
globals()[".ut"] = _ut
globals()[".r2c"] = _r2c
globals()[".c2r"] = _c2r
globals()[".reorder"] = _reorder
globals()[".subset_ltMatrices"] = _subset_lt
globals()[".Tcrossprod"] = _Tcrossprod
globals()[".adddiag"] = _adddiag
globals()[".check_obs_mean"] = _check_obs_mean
globals()[".check_obs_invcholmean"] = _check_obs_invcholmean
globals()[".colSumsdnorm"] = _colSumsdnorm
globals()["as.syMatrices"] = as_syMatrices
globals()["as.ltMatrices"] = as_ltMatrices
globals()["as.ltMatrices.syMatrices"] = _as_lt_from_sy
globals()["as.ltMatrices.ltMatrices"] = _as_lt_from_lt
globals()["as.ltMatrices.default"] = _as_lt_default
globals()["is.ltMatrices"] = is_ltMatrices
globals()["is.syMatrices"] = is_syMatrices
globals()["is.chol"] = is_chol
globals()["is.invchol"] = is_invchol
globals()["as.chol"] = as_chol
globals()["as.invchol"] = as_invchol
globals()["diagonals<-"] = set_diagonals
globals()["diagonals<-.ltMatrices"] = _set_diag_lt
globals()["diagonals<-.syMatrices"] = _set_diag_sy
globals()["diagonals.ltMatrices"] = _diagonals_lt
globals()["diagonals.syMatrices"] = _diagonals_lt
globals()["diagonals.matrix"] = _diagonals_matrix
globals()["diagonals.integer"] = _diagonals_integer
globals()["[.ltMatrices"] = bracket_lt
globals()["[.syMatrices"] = bracket_sy
globals()["dim.ltMatrices"] = dim
globals()["dim.syMatrices"] = dim
globals()["dimnames.ltMatrices"] = dimnames
globals()["dimnames.syMatrices"] = dimnames
globals()["names.ltMatrices"] = names
globals()["names.syMatrices"] = names
globals()["as.array.ltMatrices"] = as_array
globals()["as.array.syMatrices"] = as_array
globals()["print.ltMatrices"] = _print_lt
globals()["print.syMatrices"] = _print_sy
globals()["Mult.default"] = _mult_default
globals()["Mult.ltMatrices"] = _mult_lt
globals()["Mult.syMatrices"] = _mult_sy
globals()["solve.ltMatrices"] = _solve_lt
globals()["crossprod.ltMatrices"] = crossprod
globals()["crossprod.syMatrices"] = crossprod
globals()["tcrossprod.ltMatrices"] = tcrossprod
globals()["tcrossprod.syMatrices"] = tcrossprod
globals()["%*%.ltMatrices"] = Mult
globals()["%*%.syMatrices"] = Mult
globals()["chol.syMatrices"] = _chol_sy
globals()["invchol.default"] = invchol
globals()["invchol.syMatrices"] = _invchol_sy
globals()["aperm.chol"] = _aperm_chol
globals()["aperm.invchol"] = _aperm_invchol
globals()["aperm.ltMatrices"] = _aperm_lt
globals()["aperm.syMatrices"] = _aperm_sy

# Snake-case wrappers for the dotted R names.
check_obs_mean = _check_obs_mean
check_obs_invcholmean = _check_obs_invcholmean
colSumsdnorm = _colSumsdnorm
lt = _lt
ut = _ut
subset_lt = _subset_lt

as_sy_matrices = as_syMatrices
as_lt_matrices = as_ltMatrices
is_lt_matrices = is_ltMatrices
is_sy_matrices = is_syMatrices
is_chol = is_chol
is_invchol = is_invchol
as_chol = as_chol
as_invchol = as_invchol
lower_tri = Lower_tri
set_diagonals_inplace = set_diagonals
