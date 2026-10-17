"""Split a character vector into columns the way reshape2 1.4.5 does.

``colsplit`` calls ``stringr::str_split_fixed`` and then ``type.convert``
on each column with ``as.is = TRUE``. A factor input is split as its labels.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from reshape2.convert import type_convert
from reshape2.frame import Column, DataFrame, factor_labels, is_factor, is_na


_str_split_fixed = None


def _load_str_split_fixed():
    global _str_split_fixed
    if _str_split_fixed is not None:
        return _str_split_fixed
    try:
        from stringr.split import str_split_fixed
    except ImportError:
        packages = Path(__file__).resolve().parents[2]
        for name in ("stringi", "stringr"):
            path = str(packages / name)
            if path not in sys.path:
                sys.path.append(path)
        from stringr.split import str_split_fixed
    _str_split_fixed = str_split_fixed
    return _str_split_fixed


def _as_strings(string: Any) -> list[Any]:
    if isinstance(string, Column) and is_factor(string):
        return factor_labels(string)
    if isinstance(string, str) or is_na(string):
        return [string]
    if isinstance(string, Column):
        if string.storage == "character":
            return list(string.values)
        raise TypeError("colsplit string must be a character vector or a factor")
    return list(string)


def _as_names(names: Any) -> list[str]:
    if isinstance(names, str) or is_na(names):
        names = [names]
    out = []
    for name in names:
        if is_na(name):
            out.append("NA")
        else:
            out.append(str(name))
    return out


def colsplit(string: Any, pattern: Any, names: Any) -> DataFrame:
    """Split ``string`` on ``pattern`` into one column per name.

    Each column is converted with ``type.convert(..., as.is = TRUE)``.
    Integer-looking fields become integers, ``TRUE`` and ``FALSE`` become
    logical, and a field that does not fit the column type leaves the
    column as character.
    """

    str_split_fixed = _load_str_split_fixed()
    from stringi._na import NA

    texts = [NA if is_na(value) else value for value in _as_strings(string)]
    headers = _as_names(names)
    rows = str_split_fixed(texts, pattern, len(headers))
    columns = []
    for index, name in enumerate(headers):
        pieces = []
        for row in rows:
            if row is None or is_na(row):
                pieces.append(None)
            elif index < len(row):
                pieces.append(row[index])
            else:
                pieces.append("")
        columns.append((name, type_convert(pieces, as_is=True)))
    return DataFrame(columns)
