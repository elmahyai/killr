"""Return a corner of an array, from abind 1.4-8 acorn.default."""

import numpy as np

from abind.abind import Array, _copy_dimnames
from abind.asub import asub


def acorn(x, n=6, m=5, r=1, *extra_slices, addrownums=True):
    """Return a small corner of ``x`` on each margin, like ``head`` or ``tail``."""
    data, dimnames, names = _unpack(x)
    rank_dim = _rank_dim(x, data)

    n = _scalar1(n, "n")
    m = _scalar1(m, "m")
    r = _scalar1(r, "r")

    if rank_dim is None:
        length = int(data.size)
        flat = np.ravel(data, order="F")
        if n >= 0:
            count = min(n, length)
            subset = flat[:count]
            new_names = None if names is None else list(names[:count])
        else:
            count = min(-n, length)
            subset = flat[-count:]
            new_names = None if names is None else list(names[-count:])
        if isinstance(x, Array):
            return Array(subset, dimnames=dimnames, names=new_names)
        return subset

    shape = list(rank_dim)
    selectors = [_corner_indices(n, shape[0])]
    if len(shape) > 1:
        selectors.append(_corner_indices(m, shape[1]))
    if len(shape) > 2:
        selectors.append(_corner_indices(r, shape[2]))
    if len(shape) > 3:
        for axis in range(4, len(shape) + 1):
            arg_index = axis - 4
            if arg_index < len(extra_slices):
                slice_count = extra_slices[arg_index]
            else:
                slice_count = 1
            selectors.append(_corner_indices(slice_count, shape[axis - 1]))

    y = asub(x, selectors, drop=False)

    if not addrownums:
        return y

    out_dimnames = _copy_dimnames(_result_dimnames(y, dimnames))
    if out_dimnames is None:
        out_dimnames = [None] * len(shape)
    while len(out_dimnames) < len(shape):
        out_dimnames.append(None)

    for axis, selector in enumerate(selectors):
        if out_dimnames[axis] is None:
            out_dimnames[axis] = [f"[{index}]" for index in selector]

    if isinstance(y, Array):
        return Array(y.data, dimnames=out_dimnames)
    return Array(np.asarray(y), dimnames=out_dimnames)


def _scalar1(value, name):
    array = np.asarray(value)
    if array.size != 1:
        raise ValueError(f"length({name}) != 1")
    return int(array.reshape(-1)[0])


def _unpack(x):
    if isinstance(x, Array):
        return x.data, x.dimnames, x.names
    data = np.asarray(x)
    return data, None, None


def _rank_dim(x, data):
    if isinstance(x, Array) and x._r_dim is not None:
        return x._r_dim
    if isinstance(x, Array) and data.ndim == 1:
        return None
    if data.ndim == 1:
        return None
    if data.ndim == 0:
        return ()
    return tuple(int(size) for size in data.shape)


def _corner_indices(count, extent):
    count = int(count)
    extent = int(extent)
    signed = (1 if count >= 0 else -1) * min(abs(count), extent)
    if signed >= 0:
        return list(range(1, signed + 1))
    length = -signed
    end = extent
    start = end - length + 1
    return list(range(start, end + 1))


def _result_dimnames(y, fallback):
    if isinstance(y, Array):
        return y.dimnames if y.dimnames is not None else fallback
    return fallback
