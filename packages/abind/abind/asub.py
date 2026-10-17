"""Arbitrary array subsetting, from abind 1.4-8 asub.default."""

import numpy as np

from abind.abind import Array, _copy_dimnames


def asub(x, idx, dims=None, drop=None, **kwargs):
    """Subset ``x`` at ``dims`` using R-style indices in ``idx``."""
    if kwargs:
        names = list(kwargs.keys())
        if names:
            raise ValueError(
                "have unrecognized ... arguments for asub.default: " + ", ".join(names)
            )
        raise ValueError("have unrecognized unnamed ... arguments for asub.default")

    data, dimnames, names = _unpack(x)
    rank = max(len(data.shape), 1)
    if dims is None:
        dims = list(range(1, rank + 1))
    else:
        dims = [int(value) for value in np.asarray(dims).reshape(-1)]

    if len(dims) > 1 and not isinstance(idx, (list, tuple)):
        raise ValueError("idx must be a list when length dims>1")

    if not isinstance(idx, (list, tuple)):
        idx = [idx]

    if len(idx) != len(dims):
        raise ValueError("idx has different number of indices than dims")

    shape = list(data.shape) if data.ndim else [int(data.size)]
    if any(dimension < 1 or dimension > len(shape) for dimension in dims):
        raise ValueError("dims out of range")

    selectors = []
    new_dimnames = _copy_dimnames(dimnames)
    for dimension, component in zip(dims, idx):
        axis = dimension - 1
        selector, name_slice = _r_index_component(
            component, shape[axis], _dimname_at(new_dimnames, axis), drop is False
        )
        selectors.append((axis, selector))
        if new_dimnames is not None and name_slice is not None:
            new_dimnames[axis] = name_slice

    subset = _subset_like_r(data, selectors, len(shape))
    if drop is not False:
        subset = np.squeeze(subset)

    if isinstance(x, Array):
        if subset.ndim == 1 and names is not None and len(dims) == 1 and dims[0] == 1:
            return Array(subset, dimnames=new_dimnames, names=names if drop is False else None)
        return Array(subset, dimnames=_trim_dimnames(new_dimnames, subset.ndim))
    return subset


def _unpack(x):
    if isinstance(x, Array):
        return x.data, x.dimnames, x.names
    data = np.asarray(x)
    return data, None, None


def _dimname_at(dimnames, axis):
    if dimnames is None or axis >= len(dimnames):
        return None
    return dimnames[axis]


def _r_index_component(component, size, dimnames, keep_dim):
    if component is None:
        return np.arange(size), None

    if isinstance(component, str):
        component = [component]

    if isinstance(component, (list, tuple)) and component and all(
        isinstance(item, str) for item in component
    ):
        if dimnames is None:
            raise IndexError("invalid subscript type 'character'")
        lookup = {name: position for position, name in enumerate(dimnames) if name is not None}
        component = np.array([lookup[item] for item in component], dtype=int)

    array = np.asarray(component)
    if array.dtype == bool:
        return array, _slice_dimnames(dimnames, array)

    if array.ndim == 0:
        array = array.reshape(1)

    if np.issubdtype(array.dtype, np.number):
        values = array.astype(int, copy=False)
        if keep_dim and values.size == 1:
            start = int(values.reshape(-1)[0]) - 1
            selector = np.arange(start, start + 1)
            return selector, _slice_dimnames(dimnames, selector)
        selector = values - 1
        return selector, _slice_dimnames(dimnames, selector)

    return array, None


def _subset_like_r(data, selectors, ndim):
    indexers = [np.arange(data.shape[axis]) for axis in range(ndim)]
    for axis, selector in selectors:
        indexers[axis] = np.asarray(selector)
    return data[np.ix_(*indexers)]


def _slice_dimnames(dimnames, selector):
    if dimnames is None:
        return None
    if isinstance(selector, slice):
        start = 0 if selector.start is None else selector.start
        stop = len(dimnames) if selector.stop is None else selector.stop
        return list(dimnames)[start:stop]
    if isinstance(selector, np.ndarray) and selector.dtype == bool:
        return [dimnames[index] for index, keep in enumerate(selector) if keep]
    indices = np.asarray(selector).reshape(-1)
    return [dimnames[int(index)] for index in indices]


def _trim_dimnames(dimnames, ndim):
    if dimnames is None:
        return None
    if len(dimnames) <= ndim:
        out = list(dimnames)
        while len(out) < ndim:
            out.append(None)
        return out[:ndim]
    return list(dimnames[:ndim])
