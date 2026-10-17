"""SQL quoting used by glue_sql.

This is RSQLite's quoting, not a database driver. Identifiers are wrapped in
backticks and strings in single quotes. A connection object is required by
the R function and is accepted here, and it is not asked to prepare a query.
"""

from __future__ import annotations

import datetime as _datetime
import math
import re
from typing import Any

from glue._eval import identity_transformer
from glue._scan import GlueError
from glue._text import NA, SQL, Id, Glue, r_character, r_character_double
from glue.interpolate import _EMPTY, _caller_names, glue, glue_collapse, glue_data

_MISSING = object()
_COLLAPSE = re.compile(r"\*\s*$")
_BACKTICKS = re.compile(r"^`|`$")


class SQLiteConnection:
    """Marker accepted as ``con``. Quoting follows RSQLite and nothing is executed."""


sqlite = SQLiteConnection()


def quote_identifier(value: Any) -> Any:
    if isinstance(value, SQL):
        return value
    if isinstance(value, Id):
        parts = [str(quote_identifier(part)) for part in value.parts]
        return SQL(".".join(parts))
    if isinstance(value, Glue):
        value = list(value.values)
    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            return quote_identifier(value[0])
        return tuple(quote_identifier(item) for item in value)
    if value is NA or value is None:
        raise GlueError("Cannot pass NA to dbQuoteIdentifier()")
    text = value if isinstance(value, str) else r_character(value)
    if text is NA:
        raise GlueError("Cannot pass NA to dbQuoteIdentifier()")
    return SQL("`" + str(text).replace("`", "``") + "`")


def _quote_one_literal(value: Any) -> str:
    if isinstance(value, SQL):
        return str(value)
    if value is NA or value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NULL"
        return r_character_double(value)
    if isinstance(value, _datetime.datetime):
        text = value.strftime("%Y-%m-%d %H:%M:%S%z")
        return "'" + text.replace("'", "''") + "'"
    if isinstance(value, _datetime.date):
        return "'" + value.isoformat() + "'"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, Id):
        return str(quote_identifier(value))
    text = r_character(value)
    if text is NA:
        return "NULL"
    if isinstance(text, str) and not isinstance(value, (int, float, bool)):
        return "'" + text.replace("'", "''") + "'"
    return str(text)


def quote_literal(value: Any) -> Any:
    if isinstance(value, SQL):
        return value
    if isinstance(value, Glue):
        value = list(value.values)
    if isinstance(value, (list, tuple)):
        quoted = tuple(quote_literal(item) for item in value)
        if len(quoted) == 1:
            return quoted[0]
        return quoted
    return SQL(_quote_one_literal(value))


def _collapse(value: Any) -> SQL:
    collapsed = glue_collapse(value, sep=", ")
    return SQL(str(collapsed.values[0]))


def _length(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple, Glue)):
        return len(value)
    return 1


def sql_quote_transformer(con: Any, na: Any):
    del con, na

    def transformer(text: str, envir: dict[str, Any]) -> Any:
        collapse = _COLLAPSE.search(text) is not None
        if collapse:
            text = _COLLAPSE.sub("", text)
        quoted = _BACKTICKS.search(text) is not None
        if quoted:
            text = _BACKTICKS.sub("", text)
            res = quote_identifier(identity_transformer(text, envir))
        else:
            res = identity_transformer(text, envir)
            if _length(res) == 0 and collapse:
                return SQL("NULL")
            if isinstance(res, SQL):
                return _collapse(res) if collapse else res
        literal = quote_literal(res)
        if collapse:
            return _collapse(literal)
        return literal

    return transformer


def _require_con(con: Any) -> Any:
    if con is _MISSING:
        raise GlueError("`.con` is absent but must be supplied.")
    return con


def glue_sql(
    *parts: Any,
    con: Any = _MISSING,
    sep: str = "",
    envir: dict[str, Any] | None = None,
    open: str = "{",
    close: str = "}",
    na: Any = SQL("NULL"),
    null: Any = _EMPTY,
    comment: str = "#",
    literal: bool = False,
    trim: bool = True,
    **named: Any,
) -> Any:
    """Interpolate a query and quote values and backtick identifiers for RSQLite."""

    _require_con(con)
    if envir is None:
        envir = _caller_names()
    result = glue(
        *parts,
        sep=sep,
        envir=envir,
        open=open,
        close=close,
        na=na,
        null=null,
        comment=comment,
        literal=literal,
        transformer=sql_quote_transformer(con, na),
        trim=trim,
        **named,
    )
    if len(result.values) == 1:
        item = result.values[0]
        return SQL("NA" if item is NA else str(item))
    return result


def glue_data_sql(
    x: Any,
    *parts: Any,
    con: Any = _MISSING,
    sep: str = "",
    envir: dict[str, Any] | None = None,
    open: str = "{",
    close: str = "}",
    na: Any = SQL("NULL"),
    null: Any = _EMPTY,
    comment: str = "#",
    literal: bool = False,
    trim: bool = True,
    **named: Any,
) -> Any:
    """glue_data with the same SQL quoting as glue_sql."""

    _require_con(con)
    if envir is None:
        envir = _caller_names()
    result = glue_data(
        x,
        *parts,
        sep=sep,
        envir=envir,
        open=open,
        close=close,
        na=na,
        null=null,
        comment=comment,
        literal=literal,
        transformer=sql_quote_transformer(con, na),
        trim=trim,
        **named,
    )
    if len(result.values) == 1:
        item = result.values[0]
        return SQL("NA" if item is NA else str(item))
    return result


def glue_sql_collapse(x: Any, sep: str = "", width: float = math.inf, last: str = "") -> SQL:
    """Collapse values and mark the result as SQL."""

    collapsed = glue_collapse(x, sep=sep, width=width, last=last)
    item = collapsed.values[0]
    return SQL("NA" if item is NA else str(item))
