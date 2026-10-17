"""Header, body, and footer of a data frame.

``tbl_format_setup()`` decides which rows and columns fit. The other three
functions render that setup. A data frame's header is ``A data frame`` and
``dim_desc()``, which is the ``tbl`` method, not the default object summary.
"""

from __future__ import annotations

from typing import Any

from cli.styles import style_bold as cli_bold

from pillar._layout import (
    NBSP,
    big_mark,
    pluralise_n,
    session_width,
    width_print,
)
from pillar._vec import DataFrame, Matrix
from pillar._width import ansi_strip, display_extent
from pillar.colonnade import ctl_colonnade
from pillar.extent import align
from pillar.styles import format_type_sum, style_bold, style_subtle
from pillar.summary import dim_desc, type_sum
from cli.symbol import symbol


class TblFormatSetup:
    """The object ``tbl_format_setup()`` returns."""

    def __init__(self, **fields: Any):
        self.__dict__.update(fields)

    def format(self, **_ignored: Any) -> list[str]:
        lines = [cli_bold("<pillar_tbl_format_setup>")]
        lines.extend(_as_lines(tbl_format_header(self)))
        lines.extend(_as_lines(tbl_format_body(self)))
        lines.extend(_as_lines(tbl_format_footer(self)))
        return ["" if item is None else str(item) for item in lines]


def _as_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.split("\n") if value else []
    out: list[str] = []
    for item in value:
        text = "" if item is None else str(item)
        if text == "":
            out.append("")
            continue
        out.extend(text.split("\n"))
    return out


def _tbl_sum(x: Any) -> dict[str, str]:
    if isinstance(x, DataFrame):
        return {"A data frame": dim_desc(x)}
    return {"Description": str(dim_desc(x))}


def tbl_nrow(x: Any, **kwargs: Any) -> int:
    """Number of rows. A data frame uses its first dimension."""

    if kwargs:
        raise TypeError("unused arguments")
    if isinstance(x, (DataFrame, Matrix)):
        return int(x.nrow)
    if isinstance(x, dict):
        lengths = [len(values) for values in x.values()]
        return lengths[0] if lengths else 0
    if isinstance(x, (list, tuple)):
        return len(x)
    return 1


def _n_print(n: Any, rows: int) -> int:
    if n is not None and n >= 0:
        return int(n)
    maximum = int(session_width() and 20)
    from pillar._options import get_option

    print_max = int(get_option("pillar.print_max", 20))
    print_min = int(get_option("pillar.print_min", 10))
    if rows > print_max:
        return print_min
    return int(rows)


def _limit(value: Any, default: int) -> int:
    if value is not None and value >= 0:
        return int(value)
    return default


def _head(x: DataFrame, n: int) -> DataFrame:
    keep = max(0, min(int(n), x.nrow))
    return DataFrame({name: list(values)[:keep] for name, values in x.columns.items()})


_MISSING = object()


def tbl_format_setup(
    x: Any,
    width: Any = None,
    setup: Any = _MISSING,
    n: Any = None,
    max_extra_cols: Any = None,
    max_footer_lines: Any = None,
    focus: Any = None,
    **kwargs: Any,
) -> TblFormatSetup:
    """Collect the width, the rows, and the body shared by header, body, and footer.

    Pass ``setup=None`` for the header-only object. Omit it, or pass a previous
    setup, to build the body as well.
    """

    if kwargs:
        raise TypeError("unused arguments")
    if not isinstance(x, DataFrame):
        if isinstance(x, dict):
            x = DataFrame(x)
        else:
            raise TypeError("tbl_format_setup() expects a data frame")
    chosen = width_print(width)
    rows = tbl_nrow(x)
    shown = _n_print(n, rows)
    extra_limit = _limit(max_extra_cols, 100)
    footer_limit = _limit(max_footer_lines, 7)
    # A missing setup builds the body. An explicit None is the header-only object.
    if setup is None:
        return TblFormatSetup(
            x=x,
            df=None,
            width=int(chosen),
            tbl_sum=_tbl_sum(x),
            body=None,
            rows_missing=None,
            rows_total=None,
            extra_cols=None,
            extra_cols_total=None,
            max_footer_lines=None,
            abbrev_cols=None,
        )
    summary = _tbl_sum(x) if setup is _MISSING else _summary_of(setup)
    frame = _head(x, shown)
    if rows > shown:
        rows_missing: Any = rows - shown
    else:
        rows_missing = 0
    star = getattr(x, "row_names", True) is not False
    colonnade = ctl_colonnade(
        frame,
        has_row_id="*" if star else True,
        width=chosen,
        controller=x,
        focus=focus,
    )
    extra = dict(colonnade["extra_cols"])
    extra_total = len(extra)
    if extra_total > extra_limit:
        extra = dict(list(extra.items())[:extra_limit])
    return TblFormatSetup(
        x=x,
        df=frame,
        width=int(chosen),
        tbl_sum=summary,
        body=list(colonnade["body"]),
        rows_missing=rows_missing,
        rows_total=rows,
        extra_cols=extra,
        extra_cols_total=extra_total,
        max_footer_lines=footer_limit,
        abbrev_cols=list(colonnade["abbrev_cols"]),
    )


def _summary_of(setup: Any) -> dict[str, str]:
    if isinstance(setup, TblFormatSetup):
        return dict(setup.tbl_sum)
    if isinstance(setup, dict) and "tbl_sum" in setup:
        return dict(setup["tbl_sum"])
    return dict(setup)


def tbl_format_setup_header_only(x: Any, width: Any = None) -> TblFormatSetup:
    """The object returned when ``setup`` is ``NULL``."""

    chosen = width_print(width)
    return TblFormatSetup(
        x=x,
        df=None,
        width=int(chosen),
        tbl_sum=_tbl_sum(x),
        body=None,
        rows_missing=None,
        rows_total=None,
        extra_cols=None,
        extra_cols_total=None,
        max_footer_lines=None,
        abbrev_cols=None,
    )


def _format_comment(lines: list[str], width: int) -> list[str]:
    from cli.extra import ansi_strwrap
    from cli.layout import console_width

    if not lines:
        return []
    prefix = "# "
    limit = min(int(width), int(console_width()))
    budget = max(limit - int(display_extent(prefix)), 0)
    out: list[str] = []
    for line in lines:
        wrapped = ansi_strwrap(line, width=budget, indent=0, exdent=2, simplify=True)
        if isinstance(wrapped, str):
            wrapped = [wrapped]
        wrapped = [item.replace(NBSP, " ") for item in wrapped]
        out.append("\n".join(prefix + item for item in wrapped))
    return out


def _header_lines(named: dict[str, str], width: int) -> list[str]:
    if not named:
        return []
    names = list(named)
    values = [named[name] for name in names]
    if all(name == "" for name in names):
        text = values
    else:
        labels = align([name + ":" for name in names], space=NBSP)
        if isinstance(labels, str):
            labels = [labels]
        text = [label + " " + value for label, value in zip(labels, values)]
    painted = style_subtle(_format_comment(text, width))
    if isinstance(painted, str):
        return [painted]
    return list(painted)


def tbl_format_header(x: Any, setup: Any = None, **kwargs: Any) -> list[str]:
    """The comment line above the table, usually ``# A data frame: n × p``."""

    if kwargs:
        raise TypeError("unused arguments")
    if isinstance(x, TblFormatSetup):
        body = tbl_format_header(x.x, setup=x)
        return [str(cli_bold("<tbl_format_header(setup)>")), *body]
    if setup is None:
        raise TypeError('argument "setup" is missing, with no default')
    named = dict(setup.tbl_sum)
    focus = getattr(x, "pillar_focus", None)
    if focus:
        from pillar._layout import tick_if_needed

        names = tick_if_needed(list(focus))
        named["Focus columns"] = ", ".join(names)
    return _header_lines(named, int(setup.width))


def tbl_format_body(x: Any, setup: Any = None, **kwargs: Any) -> list[str]:
    """The aligned body stored on the setup."""

    if kwargs:
        raise TypeError("unused arguments")
    if isinstance(x, TblFormatSetup):
        body = tbl_format_body(x.x, setup=x)
        return [str(cli_bold("<tbl_format_body(setup)>")), *body]
    if setup is None:
        raise TypeError('argument "setup" is missing, with no default')
    body = setup.body
    if body is None:
        return []
    return list(body)


def _abbrev_name(column: Any, title: str) -> str:
    label = ansi_strip(format_type_sum(type_sum(column), None))
    if isinstance(label, list):
        label = label[0] if label else ""
    shown = style_bold(title)
    if isinstance(shown, list):
        shown = shown[0] if shown else title
    return f"{shown} {label}"


def _extra_words(setup: TblFormatSetup) -> list[str] | None:
    extra = setup.extra_cols or {}
    if len(extra) == 0:
        return None
    total = int(setup.extra_cols_total or 0)
    shown = [_abbrev_name(column, name) for name, column in extra.items()]
    if total > len(extra):
        shown.append(symbol["ellipsis"])
    if len(shown) > 1:
        shown = [item + "," if index < len(shown) - 1 else item for index, item in enumerate(shown)]
    words = [big_mark(total)]
    rows_total = setup.rows_total
    frame = setup.df
    if rows_total != 0 and frame is not None and frame.nrow > 0:
        words.append("more")
    words.append(pluralise_n("variable(s):", total))
    words.extend(shown)
    return words


def _abbrev_words(setup: TblFormatSetup) -> list[str] | None:
    abbrev = list(setup.abbrev_cols or [])
    if not abbrev:
        return None
    from cli.unicode_output import is_utf8_output
    from pillar.parts import _superdigit

    sep = "\u200b" if is_utf8_output() else ": "
    marked = []
    for index, name in enumerate(abbrev, start=1):
        text = "" if name is None else str(name)
        marked.append(_superdigit(index) + sep + text)
    if len(marked) > 1:
        marked = [item + "," if index < len(marked) - 1 else item for index, item in enumerate(marked)]
    return ["abbreviated", pluralise_n("name(s):", len(abbrev)), *marked]


def _row_words(setup: TblFormatSetup) -> list[str] | None:
    frame = setup.df
    if frame is not None and frame.ncol != 0:
        missing = setup.rows_missing
        if missing is None or (isinstance(missing, float) and missing != missing):
            return ["more", "rows"]
        if isinstance(missing, (int, float)) and not isinstance(missing, bool) and missing > 0:
            count = int(missing)
            return [big_mark(count), "more", pluralise_n("row(s)", count)]
        return None
    if frame is None:
        return None
    total = setup.rows_total
    if (total is None or (isinstance(total, float) and total != total)) and frame.nrow > 0:
        return ["at", "least", big_mark(frame.nrow), pluralise_n("row(s)", frame.nrow), "total"]
    return None


def _wrap_footer(words: list[str] | None, setup: TblFormatSetup, lines: int, use_ellipsis: bool) -> list[str]:
    from pillar._layout import distribute_pillars

    if not words or lines <= 0:
        return []
    max_extent = int(setup.width) - 1
    n_tiers = min(len(words), lines)
    extra = int(display_extent(symbol["ellipsis"])) + 1 if use_ellipsis else 0
    if n_tiers <= 0:
        return []
    tier_widths = [max_extent - 4] * max(n_tiers - 1, 0) + [max_extent - 4 - extra]
    widths = [min(int(display_extent(word)), max_extent - 4) for word in words]
    placed = distribute_pillars(widths, tier_widths)
    groups: dict[int, list[str]] = {}
    order: list[int] = []
    truncated = False
    for index, tier in enumerate(placed["tier"]):
        if tier is None:
            truncated = True
            continue
        if tier not in groups:
            groups[tier] = []
            order.append(tier)
        groups[tier].append(words[index])
    if use_ellipsis and truncated and order:
        groups[order[-1]].append(symbol["ellipsis"])
    out = []
    for position, tier in enumerate(order):
        bullet = symbol["info"] if position == 0 else " "
        out.append(" ".join(["#", bullet, *groups[tier]]))
    return out


def tbl_format_footer(x: Any, setup: Any = None, **kwargs: Any) -> list[str]:
    """Rows and columns that did not fit, each as a ``#`` info line."""

    if kwargs:
        raise TypeError("unused arguments")
    if isinstance(x, TblFormatSetup):
        body = tbl_format_footer(x.x, setup=x)
        return [str(cli_bold("<tbl_format_footer(setup)>")), *body]
    if setup is None:
        raise TypeError('argument "setup" is missing, with no default')
    chunks = [item for item in (_row_words(setup), _abbrev_words(setup), _extra_words(setup)) if item]
    lines_left = int(setup.max_footer_lines or 0)
    rendered: list[str] = []
    for words in chunks:
        current = _wrap_footer(words, setup, lines_left, True)
        rendered.extend(current)
        lines_left -= len(current)
        if lines_left <= 0:
            break
    painted = style_subtle(rendered) if rendered else []
    if isinstance(painted, str):
        return [painted]
    return list(painted)
