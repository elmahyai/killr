"""Column collectors. A one-letter string is the same shortcut readr uses."""

from __future__ import annotations


class Collector:
    def __init__(self, kind, **fields):
        self.kind = kind
        self.fields = fields

    def __str__(self) -> str:
        return f"<collector_{self.kind}>"

    __repr__ = __str__

    def copy(self) -> "Collector":
        return Collector(self.kind, **dict(self.fields))


class ColSpec:
    def __init__(self, cols, default):
        self.cols = list(cols)
        self.default = default

    def __str__(self) -> str:
        lines = ["cols("]
        if self.default.kind not in ("guess", "skip"):
            lines.append(f"  .default = col_{self.default.kind}(),")
        elif self.default.kind == "skip":
            lines[0] = "cols_only("
        for collector in self.cols:
            name = collector.fields.get("name")
            body = _collector_call(collector)
            if name:
                lines.append(f"  {name} = {body},")
            else:
                lines.append(f"  {body},")
        lines.append(")")
        return "\n".join(lines)

    __repr__ = __str__


def _collector_call(collector: Collector) -> str:
    kind = collector.kind
    if kind == "factor":
        levels = collector.fields.get("levels")
        ordered = collector.fields.get("ordered", False)
        parts = []
        if levels is not None:
            shown = ", ".join(repr(level) for level in levels)
            parts.append(f"c({shown})" if False else repr(list(levels)))
        if ordered:
            parts.append("ordered = TRUE")
        return f"col_factor({', '.join(parts)})"
    if kind in ("date", "time", "datetime"):
        fmt = collector.fields.get("format") or ""
        if fmt:
            return f'col_{kind}(format = "{fmt}")'
    return f"col_{kind}()"


def col_logical():
    return Collector("logical")


def col_integer():
    return Collector("integer")


def col_double():
    return Collector("double")


def col_character():
    return Collector("character")


def col_factor(levels=None, ordered=False, include_na=False):
    stored = None if levels is None else list(levels)
    return Collector("factor", levels=stored, ordered=bool(ordered), include_na=bool(include_na))


def col_date(format=""):
    return Collector("date", format=format or "")


def col_time(format=""):
    return Collector("time", format=format or "")


def col_datetime(format=""):
    return Collector("datetime", format=format or "")


def col_number():
    return Collector("number")


def col_skip():
    return Collector("skip")


def col_guess():
    return Collector("guess")


_SHORT = {
    "_": col_skip,
    "-": col_skip,
    "?": col_guess,
    "c": col_character,
    "f": col_factor,
    "d": col_double,
    "i": col_integer,
    "l": col_logical,
    "n": col_number,
    "D": col_date,
    "T": col_datetime,
    "t": col_time,
}


def col_concise(letter: str) -> Collector:
    if letter not in _SHORT:
        raise ValueError(f"Unknown shortcut: {letter}")
    return _SHORT[letter]()


def _as_collector(value) -> Collector:
    if isinstance(value, Collector):
        return value
    if isinstance(value, str) and len(value) == 1:
        return col_concise(value)
    raise TypeError("column types must be collectors or one-letter shortcuts")


def cols(*args, default=None, **named):
    """Name the columns you want to override. `default` is readr's `.default`."""
    collectors = []
    for value in args:
        collectors.append(_as_collector(value))
    for name, value in named.items():
        collector = _as_collector(value)
        collector.fields["name"] = name
        collectors.append(collector)
    if default is None:
        fallback = col_guess()
    else:
        fallback = _as_collector(default)
    return ColSpec(collectors, fallback)


def cols_only(*args, **named):
    """Read only the columns named here."""
    return cols(*args, default=col_skip(), **named)


def as_col_spec(value):
    """Turn NULL, a string, a list, or a spec into a column specification."""
    if value is None:
        return ColSpec([], col_guess())
    if isinstance(value, ColSpec):
        return value
    if isinstance(value, Collector):
        return ColSpec([value], col_guess())
    if isinstance(value, str):
        return ColSpec([col_concise(letter) for letter in value], col_guess())
    if isinstance(value, dict):
        return cols(**value)
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], tuple) and len(value[0]) == 2:
            return cols(**dict(value))
        return ColSpec([_as_collector(item) for item in value], col_guess())
    raise TypeError("`col_types` must be NULL, a list or a string")


def cols_condense(spec: ColSpec) -> ColSpec:
    """Keep only the columns whose type is not the most common one."""
    if not spec.cols:
        return spec
    counts: dict[str, int] = {}
    for collector in spec.cols:
        counts[collector.kind] = counts.get(collector.kind, 0) + 1
    most = sorted(kind for kind, count in counts.items() if count == max(counts.values()))[0]
    kept = [collector for collector in spec.cols if collector.kind != most]
    default = next(collector for collector in spec.cols if collector.kind == most).copy()
    default.fields.pop("name", None)
    return ColSpec(kept, default)


def collector_for_name(kind: str) -> Collector:
    return {
        "logical": col_logical,
        "integer": col_integer,
        "double": col_double,
        "character": col_character,
        "number": col_number,
        "time": col_time,
        "date": col_date,
        "datetime": col_datetime,
    }[kind]()
