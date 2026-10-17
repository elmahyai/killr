"""Drop array dimensions, from abind 1.4-8 adrop.default."""

import numpy as np

from abind.abind import Array, _copy_dimnames


def adrop(x, drop=True, named_vector=True, one_d_array=False, **kwargs):
    """Drop degenerate dimensions from an array-like object."""
    if kwargs:
        names = list(kwargs.keys())
        if names:
            raise ValueError(
                "have unrecognized ... arguments for adrop.default: " + ", ".join(names)
            )
        raise ValueError("have unrecognized unnamed ... arguments for adrop.default")

    data, dimnames, names, dim_names = _unpack(x)
    if data.ndim == 0 and not isinstance(x, Array):
        raise ValueError("require an object with a dim attribute")

    x_dim = list(data.shape)
    if data.ndim == 0:
        x_dim = [1]

    drop_idx = _parse_drop(drop, x_dim, dim_names)

    if any(value < 1 or value > len(x_dim) for value in drop_idx):
        raise ValueError("drop must contain dimension numbers")
    if any(x_dim[value - 1] != 1 for value in drop_idx):
        dropped = ", ".join(str(value) for value in drop_idx)
        raise ValueError(f"dimensions to drop ({dropped}) do not have length 1")

    keep = [index for index in range(1, len(x_dim) + 1) if index not in set(drop_idx)]
    flat = np.ravel(data, order="F")
    keep_sizes = [x_dim[index - 1] for index in keep]

    if len(keep_sizes) > 1 or (len(keep_sizes) == 1 and one_d_array):
        new_shape = tuple(keep_sizes)
        new_data = np.reshape(flat, new_shape, order="F")
        new_dimnames = None
        if dimnames is not None:
            new_dimnames = [_dimname_at(dimnames, index - 1) for index in keep]
            new_dimnames = _copy_dimnames(new_dimnames)
        if isinstance(x, Array):
            return Array(new_data, dim=new_shape, dimnames=new_dimnames, as_vector=False)
        return new_data

    if len(keep_sizes) == 1 and named_vector:
        new_data = flat.copy()
        if dimnames is not None:
            margin = _dimname_at(dimnames, keep[0] - 1)
            if margin is not None:
                if isinstance(x, Array):
                    return Array(new_data, names=list(margin), as_vector=True)
                return new_data
        if isinstance(x, Array):
            return Array(new_data, names=names, as_vector=True)
        return flat.copy()

    if isinstance(x, Array):
        return Array(flat.copy(), names=None)
    return flat.copy()


def _unpack(x):
    if isinstance(x, Array):
        data = x.data
        if data.ndim == 0:
            data = np.reshape(data, (1,), order="C")
        return data, x.dimnames, x.names, None
    data = np.asarray(x)
    if data.ndim == 1:
        raise ValueError("require an object with a dim attribute")
    return data, None, None, None


def _dimname_at(dimnames, axis):
    if dimnames is None or axis >= len(dimnames):
        return None
    return dimnames[axis]


def _parse_drop(drop, x_dim, dim_names):
    if drop is None:
        return []

    if isinstance(drop, (bool, np.bool_)):
        drop = [bool(drop)]

    if isinstance(drop, (list, tuple)) and drop and all(
        isinstance(item, (bool, np.bool_)) for item in drop
    ):
        if len(drop) != len(x_dim):
            raise ValueError("length of drop is not equal length of dim(x)")
        return [index + 1 for index, flag in enumerate(drop) if flag]

    if isinstance(drop, str):
        drop = [drop]

    if isinstance(drop, (list, tuple)) and drop and all(isinstance(item, str) for item in drop):
        if dim_names is None:
            missing = ", ".join(f"'{name}'" for name in drop)
            raise ValueError(f"dimension names {missing} not found in x")
        indices = []
        for name in drop:
            try:
                indices.append(dim_names.index(name) + 1)
            except ValueError:
                missing = ", ".join(f"'{name}'" for name in drop if name not in dim_names)
                raise ValueError(f"dimension names {missing} not found in x") from None
        return indices

    drop_arr = np.asarray(drop).reshape(-1)
    if drop_arr.size == 0:
        return []
    if not np.issubdtype(drop_arr.dtype, np.number):
        raise ValueError("drop must contain dimension numbers")
    values = [int(value) for value in drop_arr]
    if any(np.isnan(float(value)) for value in values):
        raise ValueError("drop must contain dimension numbers")
    return values
