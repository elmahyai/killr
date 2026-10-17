"""Generalized logit from gtools 3.9.5.

``p = (x - min) / (max - min)`` and the result is ``log(p / (1 - p))``.
``min`` and ``max`` follow R arithmetic, including recycling and array shape.
"""

from __future__ import annotations

import warnings

import numpy as np

_NA_INT = np.int32(-(2**31))
# R's NA real is a signaling NaN. Arithmetic quiets it and keeps the 1954 payload.
_NA_REAL_BITS = np.array([0x7FF00000000007A2], dtype=np.uint64)
_NA_REAL = _NA_REAL_BITS.view(np.float64)[0]
_LENGTH = "longer object length is not a multiple of shorter object length"
_ARRAY_VECTOR = (
    "Recycling array of length 1 in array-vector arithmetic is deprecated.\n"
    "  Use c() or as.vector() instead."
)
_VECTOR_ARRAY = (
    "Recycling array of length 1 in vector-array arithmetic is deprecated.\n"
    "  Use c() or as.vector() instead."
)
_OVERFLOW = "NAs produced by integer overflow"
_NAN = "NaNs produced"
_NON_NUMERIC = "non-numeric argument to binary operator"
_NON_CONFORMABLE = "non-conformable arrays"
_RANK = {"integer": 0, "double": 1, "complex": 2}


class _Atom:
    def __init__(self, values, shape, kind):
        self.values = values
        self.shape = shape
        self.kind = kind


_ONE = _Atom(np.array([1.0]), None, "double")


def logit(x, min=0, max=1):
    """Generalized logit of ``x`` on the interval from ``min`` to ``max``.

    A value on an endpoint is infinite. A finite value outside the interval
    is NaN, and log warns once. An ``int32`` vector uses R's 32-bit
    subtraction; a Python int is a double, matching R's numeric literal.
    """
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        left = _prepare(x)
        lower = _prepare(min)
        upper = _prepare(max)
        shifted = _binary(left, lower, _subtract)
        span = _binary(upper, lower, _subtract)
        proportion = _binary(shifted, span, _divide)
        complement = _binary(_ONE, proportion, _subtract)
        ratio = _binary(proportion, complement, _divide)
        return _materialize(_logarithm(ratio))


def _higher(left, right):
    if _RANK[left] >= _RANK[right]:
        return left
    return right


def _product(shape):
    total = 1
    for dim in shape:
        total *= int(dim)
    return total


def _prepare(value):
    if isinstance(value, np.ndarray):
        return _prepare_array(value)
    if isinstance(value, (list, tuple)):
        return _prepare_sequence(list(value))
    if isinstance(value, range):
        return _prepare_sequence(list(value))
    if isinstance(value, (str, dict, bytes)):
        raise ValueError(_NON_NUMERIC)
    return _prepare_scalar(value)


def _prepare_scalar(value):
    if value is None:
        return _Atom(np.array([], dtype=np.float64), None, "double")
    if isinstance(value, bool):
        return _Atom(np.array([np.int32(1 if value else 0)]), None, "integer")
    if isinstance(value, np.int32):
        return _Atom(np.array([np.int32(value)]), None, "integer")
    if isinstance(value, (int, np.integer)):
        return _Atom(np.array([float(value)], dtype=np.float64), None, "double")
    if isinstance(value, (float, np.floating)):
        return _Atom(np.array([float(value)], dtype=np.float64), None, "double")
    if isinstance(value, (complex, np.complexfloating)):
        return _Atom(np.array([complex(value)], dtype=np.complex128), None, "complex")
    raise ValueError(_NON_NUMERIC)


def _prepare_array(value):
    if value.ndim == 0:
        return _prepare(value.item())
    if value.dtype == np.dtype(np.float64):
        shape = tuple(int(dim) for dim in value.shape) if value.ndim >= 2 else None
        flat = value.ravel(order="F") if value.ndim >= 2 else value.reshape(-1)
        return _Atom(flat, shape, "double")
    if value.dtype == object:
        return _prepare(value.ravel(order="F").tolist())
    if np.issubdtype(value.dtype, np.character) or np.issubdtype(value.dtype, np.bytes_):
        raise ValueError(_NON_NUMERIC)
    if value.dtype != np.dtype(bool) and not np.issubdtype(value.dtype, np.number):
        raise ValueError(_NON_NUMERIC)
    shape = tuple(int(dim) for dim in value.shape) if value.ndim >= 2 else None
    flat = np.asarray(value).ravel(order="F")
    if np.issubdtype(value.dtype, np.bool_):
        return _Atom(flat.astype(np.int32), shape, "integer")
    if value.dtype == np.dtype(np.int32):
        return _Atom(np.array(flat, dtype=np.int32, copy=True), shape, "integer")
    if np.issubdtype(value.dtype, np.complexfloating):
        return _Atom(flat.astype(np.complex128), shape, "complex")
    return _Atom(flat.astype(np.float64), shape, "double")


def _prepare_sequence(items):
    if not items:
        return _Atom(np.array([], dtype=np.float64), None, "double")
    atoms = []
    for item in items:
        if isinstance(item, (list, tuple, dict, range, np.ndarray, str, bytes)):
            raise ValueError(_NON_NUMERIC)
        if item is None:
            atoms.append(_Atom(np.array([np.nan]), None, "double"))
            continue
        atoms.append(_prepare(item))
        if atoms[-1].values.size != 1:
            raise ValueError(_NON_NUMERIC)
    kind = atoms[0].kind
    for atom in atoms[1:]:
        kind = _higher(kind, atom.kind)
    return _Atom(_sequence_values(atoms, kind), None, kind)


def _sequence_values(atoms, kind):
    if kind == "integer":
        return np.array([np.int32(atom.values[0]) for atom in atoms], dtype=np.int32)
    if kind == "complex":
        out = np.empty(len(atoms), dtype=np.complex128)
        for index, atom in enumerate(atoms):
            out[index] = _as_complex(atom)
        return out
    out = np.empty(len(atoms), dtype=np.float64)
    for index, atom in enumerate(atoms):
        out[index] = _as_float(atom)
    return out


def _as_float(atom):
    if atom.kind == "integer" and int(atom.values[0]) == -2147483648:
        return _NA_REAL
    return float(np.real(atom.values[0]))


def _as_complex(atom):
    if atom.kind == "integer" and int(atom.values[0]) == -2147483648:
        return complex(_NA_REAL, 0.0)
    return complex(atom.values[0])


def _recycle(values, length):
    size = int(values.size)
    if size == length:
        return values
    if length == 0 or size == 0:
        return values[:0]
    if size == 1:
        return np.repeat(values, length)
    repeats, extra = divmod(length, size)
    if extra == 0:
        return np.tile(values, repeats)
    return np.concatenate((np.tile(values, repeats), values[:extra]))


def _binary(left, right, op):
    if left.shape is not None and right.shape is not None and left.shape != right.shape:
        raise ValueError(_NON_CONFORMABLE)
    nx = int(left.values.size)
    ny = int(right.values.size)
    length = 0 if nx == 0 or ny == 0 else max(nx, ny)
    drop = False
    if length:
        if left.shape is not None and right.shape is None and nx == 1 and ny > 1:
            warnings.warn(_ARRAY_VECTOR, RuntimeWarning, stacklevel=2)
            drop = True
        elif right.shape is not None and left.shape is None and ny == 1 and nx > 1:
            warnings.warn(_VECTOR_ARRAY, RuntimeWarning, stacklevel=2)
            drop = True
        shorter = nx if nx < ny else ny
        if shorter and length % shorter:
            warnings.warn(_LENGTH, RuntimeWarning, stacklevel=2)
    values, kind, flagged = op(
        _recycle(left.values, length),
        _recycle(right.values, length),
        left.kind,
        right.kind,
    )
    if flagged:
        warnings.warn(flagged, RuntimeWarning, stacklevel=2)
    return _Atom(values, _shape(left, right, length, drop), kind)


def _shape(left, right, length, drop):
    if length == 0:
        for atom in (left, right):
            if atom.shape is not None and _product(atom.shape) == 0:
                return atom.shape
        return None
    if drop:
        return None
    shape = left.shape if left.shape is not None else right.shape
    if shape is None:
        return None
    product = _product(shape)
    if product != length:
        raise ValueError(
            f"dims [product {product}] do not match the length of object [{length}]"
        )
    return shape


def _cast(values, src, dst):
    if src == "integer" and dst != "integer":
        raw = np.asarray(values)
        out = raw.astype(np.float64, copy=True)
        missing = raw.astype(np.int64, copy=False) == np.int64(-2147483648)
        if np.any(missing):
            out.view(np.uint64)[missing] = np.uint64(0x7FF00000000007A2)
        if dst == "complex":
            return out.astype(np.complex128)
        return out
    if dst == "complex":
        return np.asarray(values, dtype=np.complex128)
    if dst == "double":
        return np.asarray(values, dtype=np.float64)
    return np.asarray(values, dtype=np.int32)


def _subtract(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "integer":
        values, flagged = _subtract_integer(left, right)
        return values, "integer", flagged
    if kind == "double" and left_kind == "double" and right_kind == "double":
        return left - right, "double", None
    return _cast(left, left_kind, kind) - _cast(right, right_kind, kind), kind, None


def _subtract_integer(left, right):
    first = np.asarray(left, dtype=np.int64)
    second = np.asarray(right, dtype=np.int64)
    missing = (first == np.int64(-2147483648)) | (second == np.int64(-2147483648))
    diff = first - second
    overflow = (~missing) & (
        (diff <= np.int64(-2147483648)) | (diff > np.int64(2147483647))
    )
    out = np.empty(diff.shape, dtype=np.int32)
    keep = ~missing & ~overflow
    out[keep] = diff[keep]
    out[~keep] = _NA_INT
    if np.any(overflow):
        return out, _OVERFLOW
    return out, None


def _divide(left, right, left_kind, right_kind):
    kind = _higher(left_kind, right_kind)
    if kind == "integer":
        kind = "double"
    if kind == "double" and left_kind == "double" and right_kind == "double":
        return left / right, "double", None
    return _cast(left, left_kind, kind) / _cast(right, right_kind, kind), kind, None


def _logarithm(atom):
    if atom.kind == "complex":
        logged = np.log(np.asarray(atom.values, dtype=np.complex128))
        return _Atom(logged, atom.shape, "complex")
    values = atom.values if atom.kind == "double" else _cast(atom.values, atom.kind, "double")
    values = np.asarray(values, dtype=np.float64)
    # R's log stores a positive NaN. NumPy's log of a negative is a negative NaN.
    negative = np.isfinite(values) & (values < 0) if values.size else values
    if values.size and np.any(negative):
        warnings.warn(_NAN, RuntimeWarning, stacklevel=2)
    logged = np.log(values)
    if values.size and np.any(negative):
        logged = np.array(logged, dtype=np.float64, copy=True)
        logged[negative] = np.nan
    return _Atom(logged, atom.shape, "double")


def _materialize(atom):
    values = np.asarray(atom.values)
    if atom.shape is None:
        return values.reshape(-1)
    return np.reshape(values, atom.shape, order="F")
