"""Apply an analysis repeatedly to plausible values."""

from __future__ import annotations

from copy import deepcopy


def _mapping_items(mapping):
    if isinstance(mapping, dict):
        return list(mapping.items())
    if isinstance(mapping, tuple) and len(mapping) == 2 and isinstance(mapping[0], str):
        return [mapping]
    return list(mapping)


def withPV(mapping, data, action, rewrite=True, **kwargs):
    """Run ``action`` once for each plausible-value replicate.

    ``mapping`` is a dict (or sequence of ``(working_name, columns)`` pairs).
    ``data`` may be a dict of arrays or a dataframe-like object.
    """
    items = _mapping_items(mapping)
    if not items:
        raise ValueError("mapping must contain at least one plausible-value variable")
    columns = [list(cols) if not isinstance(cols, str) else [cols] for _, cols in items]
    counts = {len(x) for x in columns}
    if len(counts) != 1:
        raise ValueError("number of plausible values must be the same for all variables")
    nreps = next(iter(counts))
    results = []
    for i in range(nreps):
        if rewrite:
            current = deepcopy(data)
            for (name, _), cols in zip(items, columns):
                current[name] = data[cols[i]]
        else:
            current = deepcopy(data)
            for (name, _), cols in zip(items, columns):
                current[name] = data[cols[i]]
        results.append(action(current))
    return results
