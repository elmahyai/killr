"""transpose, tstrsplit, CJ, and setnames."""

from __future__ import annotations

import math
import re

from datatable._util import DataTableError, as_sequence, is_na
from datatable.match import chmatch


class DataTable:
    """A column list with names. methods is only the class facility this stands in for."""

    def __init__(self, columns=None, names=None):
        if columns is None:
            columns = []
        self.columns = [list(column) for column in columns]
        if names is None:
            names = [f"V{index}" for index in range(1, len(self.columns) + 1)]
        self.names = list(names)
        self.key = None

    def __len__(self):
        return len(self.columns)


def _kind(column):
    seen = "logical"
    for item in column:
        if is_na(item):
            continue
        if isinstance(item, str):
            return "character"
        if isinstance(item, float):
            seen = "double"
        elif isinstance(item, bool):
            if seen != "double":
                seen = "logical"
        elif isinstance(item, int) and seen == "logical":
            seen = "integer"
    return seen


def _promote(columns):
    rank = {"logical": 0, "integer": 1, "double": 2, "character": 3}
    best = "logical"
    for column in columns:
        kind = _kind(column)
        if rank[kind] > rank[best]:
            best = kind
    return best


def _coerce(item, kind):
    if is_na(item):
        return None
    if kind == "character":
        if isinstance(item, bool):
            return "TRUE" if item else "FALSE"
        if isinstance(item, float) and item.is_integer():
            return str(int(item))
        return str(item)
    if kind == "double":
        if isinstance(item, bool):
            return float(int(item))
        return float(item)
    if kind == "integer":
        if isinstance(item, bool):
            return int(item)
        return int(item)
    if isinstance(item, bool):
        return bool(item)
    return item


def transpose(l, fill=None, ignore_empty=False, keep_names=None, make_names=None, list_cols=False):
    """Turn a list of columns into a list of rows. Shorter columns take fill."""
    del list_cols
    if isinstance(l, DataTable):
        names = list(l.names)
        columns = [list(column) for column in l.columns]
    elif isinstance(l, list) and (len(l) == 0 or all(isinstance(item, list) for item in l)):
        names = None
        columns = [list(column) for column in l]
    else:
        raise DataTableError("l must be a list.")
    if make_names is not None:
        if isinstance(make_names, str):
            if names is None:
                raise DataTableError(f"make.names='{make_names}' not found in names of input")
            found = chmatch([make_names], names)[0]
            if found is None:
                raise DataTableError(f"make.names='{make_names}' not found in names of input")
            make_names = found
        else:
            make_names = int(make_names)
            if make_names < 1 or make_names > len(columns):
                raise DataTableError(
                    f"make.names={make_names} is out of range [1,ncol={len(columns)}]"
                )
        colnames = [None if is_na(item) else str(item) for item in columns[make_names - 1]]
        columns = columns[: make_names - 1] + columns[make_names:]
    else:
        colnames = None
    if not columns and keep_names is None:
        return []
    kept = []
    kept_names = []
    for index, column in enumerate(columns):
        if ignore_empty and len(column) == 0:
            continue
        kept.append(column)
        if names is not None:
            kept_names.append(names[index])
    columns = kept
    kind = _promote(columns) if columns else "logical"
    width = max((len(column) for column in columns), default=0)
    rows = []
    if keep_names is not None:
        rows.append(kept_names)
    for row in range(width):
        rows.append([
            _coerce(column[row], kind) if row < len(column) else _coerce(fill, kind)
            for column in columns
        ])
    if colnames is not None:
        return DataTable(rows, [keep_names, *colnames] if keep_names is not None else colnames)
    return rows


def tstrsplit(x, split, fill=None, type_convert=False, keep=None, names=False):
    """Split each string and transpose the pieces. split is a regular expression."""
    pieces = []
    for item in as_sequence(x):
        if is_na(item):
            pieces.append([None])
        else:
            pieces.append(re.split(str(split), str(item)))
    ans = transpose(pieces, fill=fill)
    if keep is None:
        keep = list(range(1, len(ans) + 1))
    else:
        keep = [int(item) for item in as_sequence(keep)]
        if not keep or min(keep) < min(1, len(ans)) or max(keep) > len(ans):
            raise DataTableError(
                f"'keep' should contain integer values between {min(1, len(ans))} and {len(ans)}."
            )
    chosen = [ans[index - 1] for index in keep]
    if type_convert is True:
        chosen = [_convert_column(column) for column in chosen]
    elif type_convert not in (False, None):
        raise DataTableError(
            "The argument 'type.convert' should be TRUE/FALSE, a function, a list of functions, "
            f"or a named list of pairs 'fun=indices' with optionally one unnamed element (a function) "
            f"but an object of type '{type(type_convert).__name__}' was provided."
        )
    if names is False or names is None:
        return chosen
    if names is True:
        labels = [f"V{index}" for index in range(1, len(chosen) + 1)]
    else:
        labels = list(as_sequence(names))
        if len(labels) != len(chosen):
            which = "ans" if keep is None else "keep"
            raise DataTableError(
                f"length(names) (= {len(labels)}) is not equal to length({which}) (= {len(chosen)})."
            )
    return DataTable(chosen, labels)


def _convert_column(column):
    values = []
    kind = "integer"
    for item in column:
        if is_na(item) or item == "":
            values.append(None)
            continue
        try:
            number = float(item)
        except (TypeError, ValueError):
            return column
        if not math.isfinite(number) or not number.is_integer():
            kind = "double"
        values.append(number)
    if kind == "integer":
        return [None if item is None else int(item) for item in values]
    return values


def _sort_column(values, unique: bool):
    def key(item):
        if is_na(item):
            return (1, "")
        if isinstance(item, str):
            return (0, item)
        return (0, item)

    ordered = sorted(values, key=key)
    if not unique:
        return ordered
    seen = []
    found = set()
    for item in ordered:
        marker = ("na",) if is_na(item) else ("v", item)
        if marker in found:
            continue
        found.add(marker)
        seen.append(item)
    return seen


def cj(*args, sorted=True, unique=False):
    """Cross join. The last vector varies fastest. sorted orders each input."""
    columns = []
    for index, arg in enumerate(args, start=1):
        values = list(as_sequence(arg))
        if sorted and any(isinstance(item, list) for item in values):
            raise DataTableError(
                f"'sorted' is TRUE but element {index} is non-atomic, which can't be sorted; try setting sorted = FALSE"
            )
        if not values:
            columns.append(values)
            continue
        if sorted:
            columns.append(_sort_column(values, unique))
        elif unique:
            columns.append(_sort_column(values, True) if False else _unique_stable(values))
        else:
            columns.append(values)
    nrow = 1
    for column in columns:
        nrow *= len(column)
    if nrow > 2147483647:
        raise DataTableError(
            f"Cross product of elements provided to CJ() would result in {nrow:.0f} rows which exceeds .Machine$integer.max == 2147483647"
        )
    if not columns:
        return DataTable([])
    rows = [[]]
    for column in columns:
        rows = [row + [item] for row in rows for item in column]
    if nrow == 0:
        width = [[] for _ in columns]
    else:
        width = [[row[index] for row in rows] for index in range(len(columns))]
    table = DataTable(width)
    if sorted:
        table.key = list(table.names)
    return table


def _unique_stable(values):
    seen = []
    found = set()
    for item in values:
        marker = ("na",) if is_na(item) else ("v", item)
        if marker in found:
            continue
        found.add(marker)
        seen.append(item)
    return seen


def setnames(x, old=None, new=None, skip_absent=False):
    """Rename columns. Passing only the new names replaces every name."""
    if not isinstance(x, DataTable):
        raise DataTableError("x is not a data.table or data.frame")
    if not isinstance(skip_absent, bool):
        raise DataTableError("skip_absent must be TRUE or FALSE")
    if new is None:
        if old is None:
            raise DataTableError("Passed a vector of type 'NULL'. Needs to be type 'character'.")
        labels = list(as_sequence(old))
        if any(not isinstance(item, str) for item in labels):
            raise DataTableError("Passed a vector of type 'double'. Needs to be type 'character'.")
        if len(labels) != len(x.names):
            raise DataTableError(f"Can't assign {len(labels)} names to a {len(x.names)}-column data.table")
        x.names = labels
        return x
    new_names = list(as_sequence(new))
    if any(not isinstance(item, str) for item in new_names):
        raise DataTableError("'new' is not a character vector or a function")
    if any(is_na(item) for item in as_sequence(old)):
        raise DataTableError("NA (or out of bounds) in 'old'")
    if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in as_sequence(old)):
        positions = []
        for item in as_sequence(old):
            position = int(item)
            if position == 0 or abs(position) > len(x.names):
                raise DataTableError("NA (or out of bounds) in 'old'")
            if position < 0:
                position = len(x.names) + 1 + position
            positions.append(position)
    else:
        wanted = [str(item) for item in as_sequence(old)]
        positions = []
        for name in wanted:
            if name not in x.names:
                if skip_absent:
                    positions.append(None)
                else:
                    raise DataTableError(
                        f"Items of 'old' not found in column names: [{name}]. Consider skip_absent=TRUE."
                    )
            else:
                positions.append(x.names.index(name) + 1)
        if skip_absent:
            paired = [(pos, label) for pos, label in zip(positions, new_names) if pos is not None]
            positions = [pos for pos, _ in paired]
            new_names = [label for _, label in paired]
    if len(new_names) != len(positions):
        raise DataTableError(f"'old' is length {len(positions)} but 'new' is length {len(new_names)}")
    for position, label in zip(positions, new_names):
        x.names[position - 1] = label
    return x
