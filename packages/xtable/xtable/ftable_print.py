"""List and ``ftable`` printers, plus small xtable sanitizing helpers.

The R implementation relies on stats' ``ftable`` formatter.  Python callers
can provide an :class:`Ftable` with its already formatted character matrix;
this keeps the port independent of a dataframe or statistics library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from xtable.caption_replacement import Xtable
from xtable.print_xtable import print_xtable
from xtable.sanitize_final import sanitize_final
from xtable.string_connection import StringConnection


def as_is(value: Any) -> Any:
    """Equivalent of R's ``as.is``: return the value unchanged."""

    return value


def as_math(value: Any, *suffix: Any) -> Any:
    """Put values in math delimiters, preserving vector-like inputs."""

    def one(item: Any) -> str:
        return "$" + str(item) + "$"

    if isinstance(value, (list, tuple)):
        return [one(item) for item in value]
    result = one(value)
    if suffix:
        result += "".join(str(item) for item in suffix)
    return result


@dataclass
class Ftable:
    """A small Python representation of an R ``ftable``.

    ``data`` is the character matrix returned by an ftable formatter.
    ``row_vars`` and ``col_vars`` contain the corresponding variable names.
    """

    data: list[list[Any]]
    row_vars: list[str] = field(default_factory=list)
    col_vars: list[str] = field(default_factory=list)


@dataclass
class XtableFtable:
    data: list[list[Any]]
    attrs: dict[str, Any]
    classes: tuple[str, ...] = ("xtableFtable", "ftable")


def xtable_ftable(
    x: Ftable | list[list[Any]],
    *,
    caption: Any = None,
    label: Any = None,
    align: list[str] | None = None,
    digits: Any = 0,
    display: list[str] | None = None,
    quote: bool = False,
    method: str = "non.compact",
    lsep: str = r" $\vert$ ",
    row_vars: list[str] | None = None,
    col_vars: list[str] | None = None,
    **_: Any,
) -> XtableFtable:
    """Attach xtable attributes to a formatted ftable matrix."""

    if method not in {"non.compact", "row.compact", "col.compact", "compact"}:
        raise ValueError("method must be one of non.compact, row.compact, col.compact, compact")
    if isinstance(x, Ftable):
        data = [list(row) for row in x.data]
        row_vars = list(x.row_vars)
        col_vars = list(x.col_vars)
    else:
        data = [list(row) for row in x]
        row_vars = [] if row_vars is None else list(row_vars)
        col_vars = [] if col_vars is None else list(col_vars)
    nr, nc = len(row_vars), len(col_vars)
    if nr == 0 and method in {"col.compact", "compact"}:
        method = "non.compact" if method == "col.compact" else "row.compact"
    if nc == 0 and method in {"row.compact", "compact"}:
        method = "non.compact" if method == "row.compact" else "col.compact"
    if method == "non.compact":
        n_char_cols, n_char_rows = nr + 2, nc + 1
    elif method == "row.compact":
        n_char_cols, n_char_rows = nr + 2, nc
    elif method == "col.compact":
        n_char_cols, n_char_rows = nr + 1, nc + 1
    else:
        n_char_cols, n_char_rows = nr + 1, nc
    if align is None:
        align = ["l"] * (n_char_cols - 1) + ["l |"] + ["r"] * (
            len(data[0]) - n_char_cols if data else 0
        )
    if display is None:
        display = ["s"] * n_char_cols + ["d"] * (
            len(data[0]) - n_char_cols if data else 0
        )
    attrs = {
        "ftableCaption": caption, "ftableLabel": label, "ftableAlign": list(align),
        "ftableDigits": digits, "quote": quote, "ftableDisplay": list(display),
        "method": method, "lsep": lsep, "nChars": [n_char_rows, n_char_cols],
        "row.vars": row_vars, "col.vars": col_vars,
    }
    return XtableFtable(data, attrs)


def _as_text(value: Any, fn: Callable[[Any], Any] | None) -> str:
    if fn is not None:
        value = fn([value])
        if isinstance(value, (list, tuple)):
            value = value[0]
    return str(value)


def print_xtable_ftable(
    x: XtableFtable,
    *,
    type: str = "latex",
    print_results: bool = False,
    sanitize_text_function: Callable[[Any], Any] | None = as_is,
    sanitize_rownames_function: Callable[[Any], Any] | None = None,
    sanitize_colnames_function: Callable[[Any], Any] | None = None,
    booktabs: bool = False,
    **kwargs: Any,
) -> str:
    """Render an :class:`XtableFtable` through the regular LaTeX printer."""

    if type.lower() != "latex":
        raise NotImplementedError("print.xtableFtable not yet implemented for this type")
    if not isinstance(x, XtableFtable):
        raise ValueError("print.xtableFtable expects an XtableFtable")
    data = [list(row) for row in x.data]
    nr = x.attrs["nChars"][0]
    nc = x.attrs["nChars"][1]
    row_fn = sanitize_rownames_function
    col_fn = sanitize_colnames_function
    if row_fn is not None:
        for i in range(min(nr, len(data))):
            for j in range(min(nc - 1, len(data[i]))):
                data[i][j] = _as_text(data[i][j], row_fn)
    if col_fn is not None:
        for i in range(min(len(x.attrs["col.vars"]), len(data))):
            if nc - 1 < len(data[i]):
                data[i][nc - 1] = _as_text(data[i][nc - 1], col_fn)
    for i in range(min(nr, len(data))):
        for j in range(nc - 1, len(data[i])):
            data[i][j] = r"\multicolumn{1}{l}{ " + str(data[i][j]) + "}"
    xt = Xtable(data, attrs={
        "caption": x.attrs["ftableCaption"], "label": x.attrs["ftableLabel"],
        "align": x.attrs["ftableAlign"], "digits": x.attrs["ftableDigits"],
        "display": x.attrs["ftableDisplay"],
    }, col_names=[], row_names=[])
    hline = kwargs.pop("hline_after", None)
    if hline is None:
        hline = [-1, nr, len(data)]
    return print_xtable(
        xt, type="latex", print_results=print_results, include_rownames=False,
        include_colnames=False, booktabs=booktabs, hline_after=hline,
        sanitize_text_function=sanitize_text_function, **kwargs
    )


def print_xtable_list(
    x: Any,
    *,
    type: str = "latex",
    colnames_format: str = "single",
    print_results: bool = False,
    **kwargs: Any,
) -> str:
    """Render an ``XtableList`` by stacking its component tables."""

    if type.lower() != "latex":
        raise NotImplementedError("print.xtableList not yet implemented for this type")
    items = list(x.items if hasattr(x, "items") else x)
    if not items:
        return ""
    first = items[0]
    rows: list[list[Any]] = []
    for item in items:
        rows.extend([list(row) for row in item.data])
    combined = Xtable(
        rows, attrs=dict(first.attrs), col_names=first.colnames(),
        row_names=[str(i + 1) for i in range(len(rows))],
    )
    combined.attrs["align"] = first.attrs.get("align", ["l"] * (combined.ncol + 1))
    combined.attrs["digits"] = first.attrs.get("digits", [0] * (combined.ncol + 1))
    combined.attrs["display"] = first.attrs.get("display", ["f"] * (combined.ncol + 1))
    if hasattr(x, "attrs"):
        combined.attrs["caption"] = x.attrs.get("caption")
        combined.attrs["label"] = x.attrs.get("label")
    return print_xtable(combined, type="latex", print_results=print_results, **kwargs)


__all__ = [
    "Ftable", "XtableFtable", "as_is", "as_math", "print_xtable_list",
    "print_xtable_ftable", "sanitize_final", "xtable_ftable",
]
