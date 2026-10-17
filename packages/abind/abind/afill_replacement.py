"""Fill an array with subarrays, from abind 1.4-8 afill<-.default."""

import numpy as np

from abind.abind import Array, _copy_dimnames
from abind.asub import asub


def afill_replacement(x, /, *args, excess_ok=False, local=True, value):
    """Assign ``value`` into ``x`` using dimnames on empty index slots."""
    del local  # caller frame semantics; Python mutates the object passed in
    target, x_dn, x_shape = _unpack_target(x)
    val, value_dn, value_shape = _unpack_value(value)

    dot_uneval = list(args)
    if dot_uneval:
        missing_dot = [item is None for item in dot_uneval]
    else:
        missing_dot = []

    x_rank = len(x_shape)
    value_rank = len(value_shape)

    if value_rank < x_rank:
        if not dot_uneval:
            raise ValueError("must supply anonymous args to show how value matches up with x")
        if sum(not flag for flag in missing_dot) + max(value_rank, 1) != max(x_rank, 1):
            need = x_rank - max(value_rank, 1)
            raise ValueError(
                f"must have {need} non-missing anon args to assign a "
                f"{max(value_rank, 1)}-d value into a {max(x_rank, 1)}-d array"
            )
    elif value_rank == x_rank:
        if not dot_uneval:
            dot_uneval = [None] * x_rank
            missing_dot = [True] * x_rank
        elif len(dot_uneval) != x_rank:
            raise ValueError(
                f"must have 0 or {x_rank} empty arguments when 'x' and 'value' have same number of dims"
            )
    else:
        raise ValueError("does not make sense to have more dims in value than x")

    if any(missing_dot) and (
        x_dn is None
        or any(
            missing_dot[index] and (x_dn[index] is None or len(x_dn[index]) == 0) and x_shape[index] != 0
            for index in range(x_rank)
        )
    ):
        raise ValueError("'x' must have names on dimensions corresponding to those in 'value'")

    if any(missing_dot) and (
        value_dn is None
        or any(
            value_dn[index] is None or len(value_dn[index]) == 0
            for index in range(len(value_dn))
            if value_rank != 0
        )
    ):
        raise ValueError("'value' must have names on dimensions corresponding to empty args on the LHS")

    dot_args = [None if missing else arg for missing, arg in zip(missing_dot, dot_uneval)]
    idxs = [None] * x_rank
    strip_excess = False
    for index in range(x_rank):
        if missing_dot[index]:
            j = sum(missing_dot[: index + 1]) - 1
            matched = _match_names(value_dn[j], x_dn[index], nomatch=0)
            idxs[index] = matched
            if np.any(matched == 0):
                if not excess_ok:
                    bad = value_dn[j][np.where(matched == 0)[0][:3]]
                    extra = " ..." if np.sum(matched == 0) > 3 else ""
                    quoted = ", ".join(f"'{name}'" for name in bad)
                    raise ValueError(
                        f"value has dimnames that are not in 'x' on dim[{index + 1}]: {quoted}{extra}"
                    )
                strip_excess = True
        else:
            idxs[index] = _lhs_index(dot_args[index], x_shape[index], x_dn[index] if x_dn else None, index + 1)

    if strip_excess:
        keepers = []
        for index, missing in enumerate(missing_dot):
            if missing:
                keepers.append(np.where(idxs[index] != 0)[0])
        val = _subset_value(val, value_shape, keepers, missing_dot)
        value_shape = list(np.asarray(val).shape) if np.asarray(val).size else []
        if isinstance(value, Array):
            value = Array(val, dim=value_shape or None, dimnames=_subset_value_dn(value_dn, keepers, missing_dot))
        else:
            value = val
        val, value_dn, value_shape = _unpack_value(value)

    if int(np.prod(value_shape) if value_shape else np.asarray(val).size) > 1 and len(np.unique(val)) > 1:
        need_rep = 1
        value_dim_cursor = 0
        for index, missing in enumerate(missing_dot):
            if missing:
                value_dim_cursor += 1
                if need_rep > 1:
                    axis = value_dim_cursor
                    reps = np.repeat(np.arange(1, value_shape[value_dim_cursor - 1] + 1), need_rep)
                    if isinstance(value, Array):
                        value = asub(value, reps, dims=axis)
                    else:
                        value = asub(val, reps, dims=axis)
                    val, value_dn, value_shape = _unpack_value(value)
                need_rep = 1
            else:
                need_rep *= len(idxs[index])

    if np.asarray(val).size:
        _assign(target, idxs, np.asarray(val, order="F"))

    if isinstance(x, Array):
        x.data = target
        return x
    if isinstance(x, np.ndarray):
        x[...] = target
        return x
    return target


def _unpack_target(x):
    if isinstance(x, Array):
        shape = list(x.data.shape) if x.data.ndim else [int(x.data.size)]
        dn = _copy_dimnames(x.dimnames)
        if x.data.ndim <= 1 and x.names is not None:
            dn = [list(x.names)]
        return x.data, dn, shape
    data = np.asarray(x)
    if data.ndim == 0:
        shape = [1]
    elif data.ndim == 1:
        shape = [int(data.size)]
    else:
        shape = list(data.shape)
    return np.array(data, copy=False), None, shape


def _unpack_value(value):
    if isinstance(value, Array):
        data = value.data
        shape = list(data.shape) if data.ndim else [int(data.size)]
        dn = _copy_dimnames(value.dimnames)
        if data.ndim <= 1 and value.names is not None:
            dn = [list(value.names)]
        return data, dn, shape
    data = np.asarray(value)
    if data.ndim == 0:
        shape = [1]
    elif data.ndim == 1:
        shape = [int(data.size)]
    else:
        shape = list(data.shape)
    names = getattr(value, "names", None)
    dn = [list(names)] if names is not None else None
    return data, dn, shape


def _match_names(from_names, to_names, nomatch):
    if from_names is None or to_names is None:
        return np.zeros(len(from_names or []), dtype=int)
    lookup = {name: position + 1 for position, name in enumerate(to_names) if name is not None}
    out = np.empty(len(from_names), dtype=int)
    for index, name in enumerate(from_names):
        if name is None:
            out[index] = nomatch if nomatch else 0
        elif name in lookup:
            out[index] = lookup[name]
        else:
            out[index] = nomatch if nomatch else 0
    return out


def _lhs_index(component, size, dimnames, dim_num):
    if isinstance(component, str):
        component = [component]
    if isinstance(component, (list, tuple)) and component and all(isinstance(item, str) for item in component):
        if dimnames is None or len(dimnames) != size:
            raise ValueError(f"'x' doesn't have dimnames on dim {dim_num}")
        lookup = {name: position + 1 for position, name in enumerate(dimnames) if name is not None}
        matched = []
        for item in component:
            if item not in lookup:
                matched.append(np.nan)
            else:
                matched.append(float(lookup[item]))
        arr = np.asarray(matched, dtype=float)
        if np.any(np.isnan(arr)):
            bad = [component[i] for i in np.where(np.isnan(arr))[0][:3]]
            quoted = ", ".join(f"'{name}'" for name in bad)
            raise ValueError(f"LHS character indicies at on dim {dim_num} not matched: {quoted}")
        return arr.astype(int)

    array = np.asarray(component)
    if array.dtype == bool:
        flags = array.reshape(-1)
        if flags.size == 1:
            flags = np.repeat(flags, size)
        elif flags.size != size:
            flags = np.resize(flags, size)
        positions = np.arange(1, size + 1)[flags]
        if np.any(np.isnan(positions)):
            raise ValueError(f"LHS logical indicies at on dim {dim_num} have NA value")
        return positions

    if np.issubdtype(array.dtype, np.number):
        values = array.astype(int, copy=False).reshape(-1)
        if values.size and np.all(values >= 0):
            if np.any(values == 0):
                values = values[values != 0]
            else:
                values = values.copy()
            if np.any(values > size):
                raise ValueError(f"LHS numeric indicies at on dim {dim_num} values too large")
            return values
        if values.size and np.all(values <= 0):
            return np.arange(1, size + 1)[values]
        raise ValueError(
            f"LHS args for indices at dim {dim_num} must be character, logical, numeric>0 or numeric<=0"
        )

    raise ValueError(
        f"LHS args for indices at dim {dim_num} must be character, logical, numeric>0 or numeric<=0"
    )


def _subset_value(val, shape, keepers, missing_dot):
    data = np.asarray(val, order="F")
    if data.ndim == 0:
        return data
    indexers = [slice(None)] * data.ndim
    cursor = 0
    for missing in missing_dot:
        if missing:
            indexers[cursor] = keepers[cursor]
            cursor += 1
    if cursor == 0:
        return data
    if cursor == 1 and data.ndim == 1:
        return data[indexers[0]]
    active = [indexers[axis] for axis in range(cursor)]
    if len(active) == 1:
        return data[active[0]]
    return data[np.ix_(*active)]


def _subset_value_dn(value_dn, keepers, missing_dot):
    if value_dn is None:
        return None
    out = _copy_dimnames(value_dn)
    cursor = 0
    for index, missing in enumerate(missing_dot):
        if missing:
            keep = keepers[cursor]
            out[cursor] = [out[cursor][i] for i in keep]
            cursor += 1
    return out


def _assign(data, idxs, value):
    if data.ndim == 0:
        data.reshape(1)[0] = value.reshape(-1)[0]
        return
    indexers = []
    for component in idxs:
        values = np.asarray(component, dtype=int).reshape(-1)
        values = values[values != 0]
        indexers.append(values - 1)
    flat_value = np.ravel(np.asarray(value, order="F"), order="F")
    if data.ndim == 1:
        if flat_value.size == 1:
            data[indexers[0]] = flat_value[0]
        else:
            data[indexers[0]] = flat_value
        return
    combos = list(_f_cartesian(indexers))
    if flat_value.size == 1:
        for combo in combos:
            data[combo] = flat_value[0]
        return
    if flat_value.size != len(combos):
        raise ValueError(
            f"cannot assign array of size {flat_value.size} into region of size {len(combos)}"
        )
    for position, combo in enumerate(combos):
        data[combo] = flat_value[position]


def _f_cartesian(indexers):
    if len(indexers) == 1:
        for item in indexers[0]:
            yield (int(item),)
        return
    for tail in _f_cartesian(indexers[1:]):
        for item in indexers[0]:
            yield (int(item),) + tail
