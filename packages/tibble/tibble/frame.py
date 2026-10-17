"""Columns with names. NumPy is not required: these are Python lists."""


class Tibble:
    """A named list of columns, the part of a tibble rematch2 builds."""

    def __init__(self, names, columns, nrow):
        self.names = list(names)
        self.columns = list(columns)
        self.nrow = int(nrow)

    def __getitem__(self, name):
        for column_name, column in zip(self.names, self.columns):
            if column_name == name:
                return column
        raise KeyError(name)

    def __len__(self):
        return self.nrow


def _length(value):
    if isinstance(value, Tibble):
        return value.nrow
    if isinstance(value, str) or value is None or isinstance(value, (int, float, bool)):
        return 1
    return len(value)


def _as_column(value, nrow):
    if hasattr(value, "rows"):
        if len(value) != nrow:
            raise ValueError("column lengths must match, or a column must have length 1")
        return value
    if isinstance(value, str) or value is None or isinstance(value, (int, float, bool)):
        return [value] * nrow
    if _length(value) == nrow:
        return list(value)
    if _length(value) == 1:
        return list(value) * nrow
    raise ValueError("column lengths must match, or a column must have length 1")


def _make_unique(names, sep):
    """Base R make.unique. The first copy keeps its name."""
    used = set(names)
    seen = set()
    out = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
            continue
        number = 1
        while True:
            candidate = f"{name}{sep}{number}"
            number += 1
            if candidate not in used:
                break
        used.add(candidate)
        out.append(candidate)
    return out


def _repair(names, prefix, sep):
    """vctrs::vec_as_names_legacy, which repair_names calls."""
    if len(names) == 0:
        return []
    blank = [name == "" for name in names]
    filled = _make_unique(
        [name for name, is_blank in zip(names, blank) if not is_blank],
        sep,
    )
    out = [""] * len(names)
    index = 0
    for position, is_blank in enumerate(blank):
        if not is_blank:
            out[position] = filled[index]
            index += 1
    taken = set(out)
    free = []
    for number in range(1, len(names) + 1):
        candidate = f"{prefix}{sep}{number}"
        if candidate not in taken:
            free.append(candidate)
    index = 0
    for position, is_blank in enumerate(blank):
        if is_blank:
            out[position] = free[index]
            index += 1
    return out


def has_name(x, name):
    """TRUE when `name` is one of the column names. This is rlang::has_name."""
    if isinstance(x, Tibble):
        names = x.names
    elif isinstance(x, dict):
        names = list(x)
    else:
        names = list(getattr(x, "names"))
    return name in names


def new_tibble(columns, nrow=None, names=None):
    """Build a tibble from columns. Names are stored as given."""
    if isinstance(columns, dict) and names is None:
        names = list(columns)
        columns = [columns[name] for name in names]
    if not isinstance(columns, list):
        raise TypeError("new_tibble() expects a list of columns")
    if len(columns) == 0:
        return Tibble([], [], 0 if nrow is None else nrow)
    if names is None:
        raise ValueError("column names must be present")
    if len(names) != len(columns):
        raise ValueError("names and columns must have the same length")
    if nrow is None:
        nrow = _length(columns[0])
    stored = [_as_column(column, nrow) for column in columns]
    return Tibble(names, stored, nrow)


def repair_names(x, prefix="V", sep=""):
    """Make column names unique. Blank names take the first free prefix numbers."""
    if not isinstance(x, Tibble):
        raise TypeError("repair_names() expects a tibble")
    if len(x.names) == 0:
        return Tibble([], [], x.nrow)
    return Tibble(_repair(list(x.names), prefix, sep), list(x.columns), x.nrow)


def tibble(rows=None, name_repair="check_unique", **columns):
    """Build a tibble from named columns. A length-1 column is recycled."""
    names = list(columns)
    values = [columns[name] for name in names]
    if rows is None:
        if not values:
            nrow = 0
        else:
            nrow = max(_length(value) for value in values)
    else:
        nrow = rows
    if name_repair == "check_unique":
        if any(name == "" for name in names) or len(set(names)) != len(names):
            raise ValueError("column names must be unique and non-empty")
    elif name_repair == "unique":
        names = _repair(names, "V", "")
    elif name_repair != "minimal":
        raise ValueError("name_repair must be check_unique, unique, or minimal")
    stored = [_as_column(value, nrow) for value in values] if names or nrow == 0 else []
    if not names:
        stored = []
    return Tibble(names, stored, nrow)
