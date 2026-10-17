"""rleid, rleidv, uniqueN, and frev."""

from __future__ import annotations

from datatable._util import DataTableError, as_sequence, column_list, is_na


def _same(left, right) -> bool:
    if is_na(left) and is_na(right):
        return True
    if is_na(left) or is_na(right):
        return False
    return left == right


def _columns(x, cols):
    if column_list(x):
        columns = [list(as_sequence(column)) for column in x]
        if cols is None:
            selected = list(range(len(columns)))
        else:
            selected = [int(col) - 1 for col in as_sequence(cols)]
            if len(selected) == 0:
                raise DataTableError("x is a list, 'cols' cannot be 0-length.")
        return [columns[index] for index in selected]
    if cols is not None:
        raise DataTableError("x is a single vector, non-NULL 'cols' doesn't make sense.")
    return [list(as_sequence(x))]


def rleidv(x, cols=None, prefix=None):
    """Run-length ids. Consecutive NA values stay in the same run."""
    if prefix is not None and (not isinstance(prefix, str) or isinstance(prefix, bool)):
        raise DataTableError("'prefix' must be NULL or a character vector of length 1.")
    columns = _columns(x, cols)
    if not columns:
        return []
    nrow = len(columns[0])
    ids = []
    current = 0
    previous = None
    for row in range(nrow):
        key = tuple(column[row] if row < len(column) else None for column in columns)
        if previous is None or any(not _same(a, b) for a, b in zip(key, previous)):
            current += 1
            previous = key
        ids.append(current)
    if prefix is not None:
        return [f"{prefix}{item}" for item in ids]
    return ids


def _prefix_ok(prefix):
    if prefix is not None and (not isinstance(prefix, str) or isinstance(prefix, bool)):
        raise DataTableError("'prefix' must be NULL or a character vector of length 1.")


def rowidv(x, cols=None, prefix=None):
    """Occurrence number of each key, in the order the rows appear."""
    _prefix_ok(prefix)
    columns = _columns(x, cols)
    if not columns:
        return []
    nrow = len(columns[0])
    seen = {}
    ids = []
    for row in range(nrow):
        key = tuple(column[row] if row < len(column) else None for column in columns)
        count = seen.get(key, 0) + 1
        seen[key] = count
        ids.append(count)
    if prefix is not None:
        return [f"{prefix}{item}" for item in ids]
    return ids


def rowid(*args, prefix=None):
    """rowid(...) is rowidv on the collected columns."""
    if len(args) == 1:
        return rowidv(args[0], prefix=prefix)
    return rowidv(list(args), prefix=prefix)


def rleid(*args, prefix=None):
    """rleid(...) is rleidv on the collected columns."""
    if len(args) == 1:
        return rleidv(args[0], prefix=prefix)
    return rleidv(list(args), prefix=prefix)


def uniqueN(x, by=None, na_rm=False):
    """Number of unique values. NA counts as one value unless na_rm is TRUE."""
    if x is None:
        return 0
    if column_list(x):
        raise DataTableError("x must be an atomic vector or a data.frame/data.table")
    values = as_sequence(x)
    if getattr(values, "ndim", 1) > 1:
        raise DataTableError("x must be an atomic vector or a data.frame/data.table")
    seen = set()
    missing = False
    for item in values:
        if is_na(item):
            if not na_rm:
                missing = True
            continue
        if isinstance(item, float):
            seen.add(float(item))
        elif isinstance(item, bool):
            seen.add(bool(item))
        else:
            seen.add(item)
    return len(seen) + (1 if missing else 0)


def frev(x):
    """Reverse an atomic vector, or the order of a plain list. A data.frame stops."""
    if getattr(x, "r_class", None) in ("data.frame", "data.table"):
        raise DataTableError("'x' should not be data.frame or data.table.")
    if column_list(x):
        return list(reversed(list(x)))
    values = as_sequence(x)
    return list(reversed(list(values)))
