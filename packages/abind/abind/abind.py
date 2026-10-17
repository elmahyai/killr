"""Combine multidimensional arrays, from abind 1.4-8."""

import math
import warnings

import numpy as np


class Array:
    """A column-major array with optional dimnames.

    ``data[i, j, ...]`` is R's ``[i+1, j+1, ...]``. A one-dimensional array
    also carries the names R prints for a vector.
    """

    def __init__(self, data, dim=None, dimnames=None, dimnames_names=None, names=None, as_vector=None):
        values = np.asarray(data)
        if dim is not None:
            values = np.reshape(
                np.ravel(values, order="F"),
                tuple(int(size) for size in dim),
                order="F",
            )
            self._r_dim = tuple(int(size) for size in dim)
        else:
            self._r_dim = None if values.ndim == 1 else tuple(int(size) for size in values.shape)
        self.data = np.array(values, order="C", copy=True)
        self.names = None if names is None else [None if item is None else str(item) for item in names]
        self.dimnames = _copy_dimnames(dimnames)
        if self.dimnames is None and self.names is not None and self.data.ndim <= 1:
            self.dimnames = [list(self.names)]
        self.dimnames_names = (
            None if dimnames_names is None else [None if item is None else str(item) for item in dimnames_names]
        )
        if (
            as_vector is not False
            and self.data.ndim == 1
            and self.names is None
            and self.dimnames
            and self.dimnames[0] is not None
        ):
            self.names = list(self.dimnames[0])
            self._r_dim = None

    def __array__(self, dtype=None, copy=None):
        out = self.data
        if dtype is not None:
            out = np.asarray(out, dtype=dtype)
        elif copy:
            out = np.array(out, copy=True)
        return out

    def __repr__(self):
        return self._format()

    def __str__(self):
        return self._format()

    def _format(self):
        data = self.data
        if data.ndim == 0:
            return _fmt(data.reshape(-1)[0])
        if data.ndim == 1:
            header = ""
            if self.dimnames and self.dimnames[0]:
                header = " ".join("" if item is None else str(item) for item in self.dimnames[0]) + "\n"
            body = " ".join(_fmt(value) for value in data)
            return header + body
        return _format_margin(data, self.dimnames, prefix="")


class DataFrame:
    """A numeric frame that ``abind`` sends through ``as.matrix``."""

    def __init__(self, columns, row_names=None, col_names=None):
        if col_names is not None:
            self.col_names = [str(name) for name in col_names]
            self.columns = [np.asarray(column).reshape(-1) for column in columns]
        elif isinstance(columns, dict):
            self.col_names = [str(key) for key in columns.keys()]
            self.columns = [np.asarray(columns[key]).reshape(-1) for key in columns.keys()]
        else:
            self.columns = [np.asarray(column).reshape(-1) for column in columns]
            self.col_names = [f"V{index}" for index in range(1, len(self.columns) + 1)]
        self.row_names = None if row_names is None else [str(item) for item in row_names]
        self.is_data_frame = True


def abind(
    *args,
    along=None,
    rev_along=None,
    new_names=None,
    force_array=True,
    make_names=None,
    use_anon_names=False,
    use_first_dimnames=False,
    hier_names=False,
    use_dnns=False,
    **named,
):
    """Bind arrays along one margin.

    Positional arguments are unnamed. Keyword arguments other than the
    formals are named arrays, in the same role as names in R's ``...``.
    One list or dict of arrays is the single list argument.
    """

    hier = _hier_names(hier_names)
    if make_names is None:
        make_names = bool(use_anon_names)
    pieces, arg_names = _collect(args, named)
    if len(pieces) == 1 and _is_binding_list(pieces[0]):
        if make_names:
            raise ValueError("cannot have make.names=TRUE with a list argument")
        pieces, arg_names = _unwrap_list(pieces[0])
    elif pieces and _is_binding_list(pieces[0]) and len(pieces) != 1:
        raise ValueError("can only supply one list-valued argument for ...")
    kept = [(piece, name) for piece, name in zip(pieces, arg_names) if piece is not None]
    if not kept:
        return None
    parsed = []
    names = []
    for piece, name in kept:
        try:
            parsed.append(_parse(piece))
        except _NonAtomic:
            parsed.append(None)
        names.append("" if name is None else str(name))
    if _is_character_new_names(new_names):
        names = _apply_character_names(names, new_names)
        new_names = None
    alt_names = [name if name else f"X{index}" for index, name in enumerate(names, start=1)]
    if make_names:
        names = list(alt_names)
    rank = max([1] + [_rank(piece) for piece in parsed if piece is not None])
    along_value = _resolve_along(along, rev_along, rank)
    along_value, rank = _adjust_along(along_value, rank)
    if not force_array and rank == 2 and along_value in (1, 2):
        if along_value == 2:
            return _cbind(parsed, names, alt_names)
        return _rbind(parsed, names, alt_names)
    return _bind_arrays(
        parsed,
        names,
        alt_names,
        rank,
        along_value,
        new_names,
        use_first_dimnames,
        hier,
        use_dnns,
    )


def _hier_names(hier_names):
    if isinstance(hier_names, str):
        return _match_arg(hier_names, ("before", "after", "none"))
    if isinstance(hier_names, np.ndarray) and hier_names.dtype.kind in "SU" and hier_names.size == 1:
        return _match_arg(str(hier_names.reshape(-1)[0]), ("before", "after", "none"))
    if _r_true(hier_names):
        return "before"
    return "no"


def _match_arg(value, choices):
    exact = [choice for choice in choices if choice == value]
    if len(exact) == 1:
        return exact[0]
    partial = [choice for choice in choices if choice.startswith(value)]
    if len(partial) == 1 and value != "":
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices)
    raise ValueError(f"'arg' should be one of {quoted}")


def _r_true(value):
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise ValueError(f"'length = {value.size}' in coercion to 'logical(1)'")
        value = value.reshape(-1)[0]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("missing value where TRUE/FALSE needed")
    return bool(value)


def _collect(args, named):
    pieces = list(args)
    arg_names = [""] * len(pieces)
    reserved = {
        "along",
        "rev_along",
        "new_names",
        "force_array",
        "make_names",
        "use_anon_names",
        "use_first_dimnames",
        "hier_names",
        "use_dnns",
    }
    for key, value in named.items():
        if key in reserved:
            raise TypeError(f"abind() got multiple values for argument '{key}'")
        pieces.append(value)
        arg_names.append(key)
    if not pieces:
        raise ValueError("subscript out of bounds")
    return pieces, arg_names


def _is_scalar(value):
    if value is None or isinstance(value, (str, bytes, bool, int, float, complex)):
        return True
    if isinstance(value, np.generic):
        return True
    return isinstance(value, np.ndarray) and value.ndim == 0


def _is_data_frame(value):
    return isinstance(value, DataFrame) or getattr(value, "is_data_frame", False) is True


def _is_binding_list(value):
    if _is_data_frame(value) or isinstance(value, (Array, np.ndarray)):
        return False
    if isinstance(value, dict):
        if not value:
            return True
        if any(item is None for item in value.values()):
            return True
        return not all(_is_scalar(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        if not value:
            return False
        return not all(_is_scalar(item) for item in value)
    return False


def _unwrap_list(value):
    if isinstance(value, dict):
        return list(value.values()), ["" if key is None else str(key) for key in value.keys()]
    pieces = list(value)
    return pieces, [""] * len(pieces)


class _NonAtomic(Exception):
    pass


class _Piece:
    def __init__(self, kind, data, dimnames=None, dimnames_names=None, names=None, columns=None, col_names=None, row_names=None):
        self.kind = kind
        self.data = data
        self.dimnames = dimnames
        self.dimnames_names = dimnames_names
        self.names = names
        self.columns = columns
        self.col_names = col_names
        self.row_names = row_names


def _parse(value):
    if _is_data_frame(value):
        columns = [np.asarray(column).reshape(-1) for column in value.columns]
        col_names = [str(name) for name in value.col_names]
        row_names = None if value.row_names is None else [str(item) for item in value.row_names]
        return _Piece("df", None, columns=columns, col_names=col_names, row_names=row_names)
    if isinstance(value, Array):
        if value.data.ndim <= 1:
            names = value.names
            if names is None and value.dimnames and value.dimnames[0] is not None:
                names = list(value.dimnames[0])
            return _Piece("vector", np.asarray(value.data).reshape(-1), names=names)
        return _Piece(
            "array",
            value.data,
            dimnames=_copy_dimnames(value.dimnames),
            dimnames_names=None if value.dimnames_names is None else list(value.dimnames_names),
        )
    if isinstance(value, np.ndarray):
        if value.ndim <= 1:
            return _Piece("vector", np.asarray(value).reshape(-1))
        return _Piece("array", value)
    if isinstance(value, dict):
        if all(_is_scalar(item) for item in value.values()):
            return _Piece(
                "vector",
                _vector_from_scalars(list(value.values())),
                names=[str(key) for key in value.keys()],
            )
        raise _NonAtomic
    if isinstance(value, (list, tuple)):
        if all(_is_scalar(item) for item in value):
            return _Piece("vector", _vector_from_scalars(list(value)))
        raise _NonAtomic
    if _is_scalar(value):
        return _Piece("vector", _vector_from_scalars([value]))
    raise _NonAtomic


def _vector_from_scalars(values):
    if not values:
        return np.asarray([], dtype=float)
    if any(item is None for item in values):
        present = [item for item in values if item is not None]
        if any(isinstance(item, str) for item in present):
            return np.asarray(["NA" if item is None else str(item) for item in values])
        return np.asarray([np.nan if item is None else item for item in values], dtype=float)
    if all(isinstance(item, str) for item in values):
        return np.asarray(values)
    if all(isinstance(item, (bool, np.bool_)) for item in values):
        return np.asarray(values, dtype=bool)
    return np.asarray(values)


def _rank(piece):
    if piece is None:
        return 0
    if piece.kind == "df":
        return 2
    if piece.kind == "vector":
        return 0
    return max(piece.data.ndim, 1)


def _resolve_along(along, rev_along, rank):
    if rev_along is not None:
        rev_value = _as_along_number(rev_along)
        return rank + 1 - rev_value
    if along is None:
        return rank
    return _as_along_number(along)


def _as_along_number(value):
    array = np.asarray(value)
    if array.size != 1:
        raise ValueError(f"'length = {array.size}' in coercion to 'logical(1)'")
    number = float(array.reshape(-1)[0])
    if math.isnan(number):
        raise ValueError("missing value where TRUE/FALSE needed")
    return number


def _adjust_along(along, rank):
    fractional = along > math.floor(along) and along < math.ceil(along)
    if along < 1 or along > rank or fractional:
        rank = rank + 1
        along = max(1, min(rank + 1, math.ceil(along)))
    if along < 1 or along > rank + 1:
        raise ValueError(
            '"along" must specify one dimension of the array,\n'
            "or interpolate between two dimensions of the array"
        )
    if along > rank or along < 0:
        raise ValueError(f"along must be between 0 and {rank}")
    return int(along), rank


def _apply_character_names(names, new_names):
    if isinstance(new_names, str):
        labels = [new_names]
    else:
        labels = [str(item) for item in new_names]
    updated = list(names)
    for index, label in enumerate(labels):
        if index >= len(updated):
            raise ValueError("subscript out of bounds")
        if len(label) > 0:
            updated[index] = label
    return updated


def _is_character_new_names(new_names):
    if new_names is None or isinstance(new_names, dict):
        return False
    if isinstance(new_names, str):
        return True
    if isinstance(new_names, (list, tuple)):
        return all(isinstance(item, str) for item in new_names)
    return False


def _bind_arrays(parsed, names, alt_names, rank, along, new_names, use_first, hier, use_dnns):
    n_args = len(parsed)
    # seq(to = N - 1, length.out = N - along) ends at N - 1.
    pre = list(range(1, along))
    post = list(range(along, rank))
    perm = [index for index in range(1, rank + 1) if index != along] + [along]
    identity = perm == list(range(1, rank + 1))
    arg_dim = np.zeros((rank, n_args), dtype=int)
    dimnames_m = [[None for _ in range(n_args)] for _ in range(rank)]
    dnns_m = [[None for _ in range(n_args)] for _ in range(rank)]
    prepared = []
    for index, piece in enumerate(parsed):
        if piece is None:
            raise ValueError(f"arg '{alt_names[index]}' is non-atomic")
        data, dimnames, dnn = _coerce_piece(piece)
        new_dim = list(data.shape)
        if len(new_dim) == rank:
            if dimnames is not None:
                for axis in range(rank):
                    dimnames_m[axis][index] = dimnames[axis] if axis < len(dimnames) else None
                if use_dnns and dnn is not None:
                    for axis in range(rank):
                        dnns_m[axis][index] = dnn[axis] if axis < len(dnn) else None
            arg_dim[:, index] = new_dim
        elif len(new_dim) == rank - 1:
            if dimnames is not None:
                dest = [axis for axis in range(rank) if axis != along - 1]
                for slot, axis in enumerate(dest):
                    dimnames_m[axis][index] = dimnames[slot] if slot < len(dimnames) else None
                if use_dnns and dnn is not None:
                    for slot, axis in enumerate(dest):
                        dnns_m[axis][index] = dnn[slot] if slot < len(dnn) else None
            expanded = [new_dim[item - 1] for item in pre] + [1] + [new_dim[item - 1] for item in post]
            arg_dim[:, index] = expanded
            if not identity:
                data = _reshape_f(data, expanded)
        else:
            raise ValueError(
                f"'{alt_names[index]}' does not fit: should have `length(dim())'={rank} or {rank - 1}"
            )
        if not identity:
            data = np.transpose(data, tuple(item - 1 for item in perm))
        prepared.append(data)
    conform = arg_dim[:, 0]
    for index in range(n_args):
        mismatch = [
            axis for axis in range(rank) if axis != along - 1 and int(conform[axis]) != int(arg_dim[axis, index])
        ]
        if mismatch:
            have = ", ".join(str(int(arg_dim[axis, index])) for axis in range(rank))
            need = ", ".join("X" if axis == along - 1 else str(int(conform[axis])) for axis in range(rank))
            raise ValueError(
                f"arg '{alt_names[index]}' has dims={have}; but need dims={need}"
            )
    dimnames_new = [None] * rank
    dnn_new = [None] * rank
    if rank > 1:
        axes = [axis for axis in range(rank) if axis != along - 1]
        order = range(n_args) if use_first else range(n_args - 1, -1, -1)
        for axis in axes:
            for index in order:
                found = dimnames_m[axis][index]
                if found is not None and len(found) > 0:
                    dimnames_new[axis] = list(found)
                    if use_dnns and dnns_m[axis][index] is not None:
                        dnn_new[axis] = dnns_m[axis][index]
                    break
    use_along_names = any(name != "" for name in names)
    along_names = None
    for index, name in enumerate(names):
        size = int(arg_dim[along - 1, index])
        if size > 0:
            existing = dimnames_m[along - 1][index]
            if existing is not None and len(existing) == size:
                use_along_names = True
                if hier == "before" and name != "":
                    chunk = [f"{name}.{part}" for part in existing]
                elif hier == "after" and name != "":
                    chunk = [f"{part}.{name}" for part in existing]
                else:
                    chunk = list(existing)
            elif size == 1:
                chunk = [name]
            elif name == "":
                chunk = [""] * size
            else:
                chunk = [f"{name}{offset}" for offset in range(1, size + 1)]
            along_names = chunk if along_names is None else along_names + chunk
        if use_dnns:
            collected = [item for item in dnns_m[along - 1] if item is not None]
            if collected:
                if not use_first:
                    collected = list(reversed(collected))
                dnn_new[along - 1] = collected[0]
    if not use_along_names:
        along_names = None
    dimnames_new[along - 1] = along_names
    dtype = _common_dtype(prepared)
    flat = [np.ravel(np.asarray(block, dtype=dtype), order="F") for block in prepared]
    values = np.concatenate(flat) if flat else np.asarray([], dtype=dtype)
    other = [int(arg_dim[axis, 0]) for axis in range(rank) if axis != along - 1]
    out_shape = other + [int(np.sum(arg_dim[along - 1, :]))]
    data = _reshape_f(values, out_shape)
    if not identity:
        order = sorted(range(rank), key=lambda axis: perm[axis])
        data = np.transpose(data, tuple(order))
    if isinstance(new_names, dict):
        new_keys = list(new_names.keys())
        new_values = list(new_names.values())
        new_names = new_values
    else:
        new_keys = None
    if new_names is not None:
        for axis in range(rank):
            if axis >= len(new_names):
                raise ValueError("subscript out of bounds")
            component = new_names[axis]
            if component is None:
                pass
            else:
                labels = _name_vector(component)
                if len(labels) == data.shape[axis]:
                    dimnames_new[axis] = labels
                elif len(labels):
                    warnings.warn(
                        f"Component {axis + 1} of new.names ignored: has length {len(labels)}, should be {data.shape[axis]}",
                        stacklevel=2,
                    )
            if use_dnns and new_keys is not None and axis < len(new_keys) and new_keys[axis] != "":
                dnn_new[axis] = str(new_keys[axis])
    if use_dnns and any(item is not None for item in dnn_new):
        dnn_new = ["" if item is None else item for item in dnn_new]
    else:
        dnn_new = None
    return Array(np.array(data, order="C", copy=True), dimnames=dimnames_new, dimnames_names=dnn_new)


def _coerce_piece(piece):
    if piece.kind == "df":
        data, dimnames = _frame_matrix(piece)
        return data, dimnames, None
    if piece.kind == "vector":
        data = np.asarray(piece.data).reshape(-1)
        dimnames = None
        if piece.names is not None and data.ndim == 1:
            dimnames = [list(piece.names)]
        return data, dimnames, None
    dimnames = _copy_dimnames(piece.dimnames)
    dnn = None
    if piece.dimnames_names is not None:
        dnn = list(piece.dimnames_names)
    return np.array(piece.data, copy=True), dimnames, dnn


def _frame_matrix(piece):
    columns = piece.columns
    ncol = len(columns)
    nrow = int(columns[0].shape[0]) if ncol else 0
    if ncol == 0:
        data = np.zeros((nrow, 0))
    else:
        dtype = _common_dtype(columns)
        data = np.empty((nrow, ncol), dtype=dtype, order="F")
        for index, column in enumerate(columns):
            data[:, index] = np.asarray(column, dtype=dtype).reshape(-1)
        data = np.array(data, order="C", copy=True)
    return data, [piece.row_names, list(piece.col_names)]


def _reshape_f(data, shape):
    shape = tuple(int(size) for size in shape)
    flat = np.ravel(np.asarray(data), order="F")
    if not shape:
        shape = (flat.size,)
    return np.reshape(flat, shape, order="F")


def _common_dtype(blocks):
    if not blocks:
        return np.dtype(float)
    kinds = [np.asarray(block).dtype.kind for block in blocks]
    if any(kind in "SUO" for kind in kinds):
        return np.dtype(object)
    if any(kind == "c" for kind in kinds):
        return np.dtype(complex)
    if any(kind == "f" for kind in kinds):
        return np.dtype(float)
    if any(kind in "iu" for kind in kinds):
        return np.dtype(int)
    if all(kind == "b" for kind in kinds):
        return np.dtype(bool)
    return np.dtype(float)


def _name_vector(component):
    if isinstance(component, str):
        return [component]
    if isinstance(component, np.ndarray):
        return [str(item) for item in component.reshape(-1)]
    return [str(item) for item in component]


def _copy_dimnames(dimnames):
    if dimnames is None:
        return None
    copied = []
    for margin in dimnames:
        if margin is None:
            copied.append(None)
        else:
            copied.append([str(item) for item in margin])
    return copied


def _cbind(parsed, names, alt_names):
    return _bind_margin(parsed, names, alt_names, columns=True)


def _rbind(parsed, names, alt_names):
    return _bind_margin(parsed, names, alt_names, columns=False)


def _bind_margin(parsed, names, alt_names, columns):
    frames = [piece for piece in parsed if piece is not None and piece.kind == "df"]
    if frames and all(piece is not None and piece.kind == "df" for piece in parsed):
        if columns:
            return _bind_frames(parsed, axis=1)
        return _bind_frames(parsed, axis=0)
    blocks = []
    for index, piece in enumerate(parsed):
        if piece is None:
            raise ValueError(f"arg '{alt_names[index]}' is non-atomic")
        blocks.append(_margin_block(piece, names[index], columns))
    if columns:
        matrix_rows = None
        for index, (data, row_names, col_names, is_vector) in enumerate(blocks, start=1):
            if is_vector:
                continue
            if matrix_rows is None:
                matrix_rows = data.shape[0]
            elif data.shape[0] != matrix_rows:
                raise ValueError(f"number of rows of matrices must match (see arg {index})")
        if matrix_rows is None:
            rows = max(data.shape[0] for data, row_names, col_names, is_vector in blocks)
        else:
            rows = matrix_rows
        width = 0
        stored = []
        for index, (data, row_names, col_names, is_vector) in enumerate(blocks, start=1):
            data, row_names = _recycle_to(data, row_names, rows, index, is_vector, along_rows=True)
            stored.append((data, row_names, col_names))
            width += data.shape[1]
        out = np.empty((rows, width), dtype=_common_dtype([item[0] for item in stored]), order="F")
        cursor = 0
        col_labels = []
        any_cols = False
        row_labels = None
        for data, row_names, col_names in stored:
            count = data.shape[1]
            out[:, cursor : cursor + count] = data
            if col_names is None:
                col_labels.extend([None] * count)
            else:
                any_cols = True
                col_labels.extend(col_names)
            if row_labels is None and row_names is not None and len(row_names) == rows:
                row_labels = list(row_names)
            cursor += count
        if any_cols:
            col_labels = ["" if item is None else item for item in col_labels]
        else:
            col_labels = None
        dimnames = None if row_labels is None and col_labels is None else [row_labels, col_labels]
        return Array(np.array(out, order="C", copy=True), dimnames=dimnames)
    matrix_cols = None
    for data, row_names, col_names, is_vector in blocks:
        if is_vector:
            continue
        if matrix_cols is None:
            matrix_cols = data.shape[1]
        elif data.shape[1] != matrix_cols:
            raise ValueError("numbers of columns of arguments do not match")
    if matrix_cols is None:
        cols = max(data.shape[1] for data, row_names, col_names, is_vector in blocks)
    else:
        cols = matrix_cols
    height = 0
    stored = []
    for index, (data, row_names, col_names, is_vector) in enumerate(blocks, start=1):
        data, col_names = _recycle_to(data, col_names, cols, index, is_vector, along_rows=False)
        stored.append((data, row_names, col_names))
        height += data.shape[0]
    out = np.empty((height, cols), dtype=_common_dtype([item[0] for item in stored]), order="F")
    cursor = 0
    row_labels = []
    any_rows = False
    col_labels = None
    for data, row_names, col_names in stored:
        count = data.shape[0]
        out[cursor : cursor + count, :] = data
        if row_names is None:
            row_labels.extend([None] * count)
        else:
            any_rows = True
            row_labels.extend(row_names)
        if col_labels is None and col_names is not None and len(col_names) == cols:
            col_labels = list(col_names)
        cursor += count
    if any_rows:
        row_labels = ["" if item is None else item for item in row_labels]
    else:
        row_labels = None
    dimnames = None if row_labels is None and col_labels is None else [row_labels, col_labels]
    return Array(np.array(out, order="C", copy=True), dimnames=dimnames)


def _recycle_to(data, labels, length, index, is_vector, along_rows):
    have = data.shape[0] if along_rows else data.shape[1]
    if have == length:
        return data, labels
    if not is_vector:
        if along_rows:
            raise ValueError(f"number of rows of matrices must match (see arg {index})")
        raise ValueError("numbers of columns of arguments do not match")
    if have == 0 or length % have != 0:
        if along_rows:
            warnings.warn(
                f"number of rows of result is not a multiple of vector length (arg {index})",
                stacklevel=3,
            )
        else:
            warnings.warn(
                f"number of columns of result is not a multiple of vector length (arg {index})",
                stacklevel=3,
            )
    if have == 0:
        if along_rows:
            data = np.zeros((length, data.shape[1]), dtype=data.dtype)
        else:
            data = np.zeros((data.shape[0], length), dtype=data.dtype)
        return data, None
    reps = int(math.ceil(length / have))
    if along_rows:
        data = np.tile(data, (reps, 1))[:length, :]
    else:
        data = np.tile(data, (1, reps))[:, :length]
    if labels is not None and len(labels) != length:
        if len(labels) and length % len(labels) == 0:
            labels = (list(labels) * (length // len(labels)))[:length]
        else:
            labels = None
    return data, labels


def _margin_block(piece, arg_name, columns):
    if piece.kind == "df":
        data, dimnames = _frame_matrix(piece)
        return data, dimnames[0], dimnames[1], False
    if piece.kind == "vector" or piece.data.ndim <= 1:
        values = np.asarray(piece.data if piece.kind == "vector" else piece.data).reshape(-1)
        if columns:
            data = values.reshape(-1, 1)
            row_names = list(piece.names) if piece.names is not None else None
            col_names = [arg_name] if arg_name else None
            return data, row_names, col_names, True
        data = values.reshape(1, -1)
        row_names = [arg_name] if arg_name else None
        col_names = list(piece.names) if piece.names is not None else None
        return data, row_names, col_names, True
    data = np.asarray(piece.data)
    if data.ndim != 2:
        raise ValueError("number of rows of matrices must match (see arg 2)")
    row_names = None
    col_names = None
    if piece.dimnames is not None:
        if len(piece.dimnames) > 0:
            row_names = piece.dimnames[0]
        if len(piece.dimnames) > 1:
            col_names = piece.dimnames[1]
    return np.array(data, copy=True), row_names, col_names, False


def _bind_frames(parsed, axis):
    if axis == 1:
        columns = []
        col_names = []
        row_names = None
        nrow = None
        for piece in parsed:
            if nrow is None:
                nrow = int(piece.columns[0].shape[0]) if piece.columns else 0
                row_names = piece.row_names
            columns.extend(piece.columns)
            col_names.extend(piece.col_names)
        return DataFrame(columns, row_names=row_names, col_names=col_names)
    ncol = None
    columns = None
    col_names = None
    row_names = []
    for piece in parsed:
        count = len(piece.columns)
        if ncol is None:
            ncol = count
            columns = [np.asarray(column).reshape(-1) for column in piece.columns]
            col_names = list(piece.col_names)
        elif count != ncol:
            raise ValueError("numbers of columns of arguments do not match")
        else:
            for index in range(ncol):
                columns[index] = np.concatenate([columns[index], np.asarray(piece.columns[index]).reshape(-1)])
        if piece.row_names is None:
            length = int(piece.columns[0].shape[0]) if piece.columns else 0
            row_names.extend([""] * length)
        else:
            row_names.extend(piece.row_names)
    if columns is None:
        return DataFrame({}, row_names=[])
    explicit = row_names if any(item != "" for item in row_names) else None
    return DataFrame(columns, row_names=explicit, col_names=col_names)


def _fmt(value):
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, str):
        return value
    if value is None:
        return "NA"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    if number == math.trunc(number) and abs(number) < 1e16:
        return str(int(number))
    return format(number, ".15g")


def _format_margin(data, dimnames, prefix):
    if data.ndim == 2:
        return _format_matrix(data, dimnames, prefix)
    last = data.shape[-1]
    last_names = None
    if dimnames is not None and len(dimnames) >= data.ndim:
        last_names = dimnames[-1]
    blocks = []
    inner_names = None if dimnames is None else dimnames[:-1]
    for index in range(last):
        label = str(index + 1)
        if last_names and index < len(last_names) and last_names[index] not in (None, ""):
            label = str(last_names[index])
        blocks.append(prefix + ", , " + label + "\n\n" + _format_margin(data[(slice(None),) * (data.ndim - 1) + (index,)], inner_names, prefix))
    return "\n\n".join(blocks)


def _format_matrix(data, dimnames, prefix):
    row_names = None
    col_names = None
    if dimnames is not None:
        if len(dimnames) > 0:
            row_names = dimnames[0]
        if len(dimnames) > 1:
            col_names = dimnames[1]
    nrow, ncol = data.shape
    if ncol == 0:
        lines = []
        if row_names:
            lines.extend(str(item) for item in row_names)
        return "\n".join(lines)
    body = [[_fmt(data[row, col]) for col in range(ncol)] for row in range(nrow)]
    widths = [0] * ncol
    for col in range(ncol):
        labels = [row[col] for row in body]
        if col_names and col < len(col_names) and col_names[col] not in (None, ""):
            labels.append(str(col_names[col]))
        elif col_names is None:
            labels.append(f"[,{col + 1}]")
        widths[col] = max(len(label) for label in labels)
    header = []
    lead = 0
    if row_names:
        lead = max(len(str(item)) for item in row_names)
    if col_names is None:
        for col in range(ncol):
            header.append(f"[,{col + 1}]".rjust(widths[col]))
    else:
        for col in range(ncol):
            label = "" if col_names[col] in (None, "") else str(col_names[col])
            header.append(label.rjust(widths[col]))
    lines = [prefix + (" " * (lead + (1 if lead else 0))) + " ".join(header)]
    for row in range(nrow):
        cells = [body[row][col].rjust(widths[col]) for col in range(ncol)]
        if row_names:
            label = "" if row_names[row] in (None, "") else str(row_names[row])
            lines.append(prefix + label.rjust(lead) + " " + " ".join(cells))
        else:
            row_label = f"[{row + 1},]"
            lines.append(prefix + row_label + " " + " ".join(cells))
    return "\n".join(lines)
