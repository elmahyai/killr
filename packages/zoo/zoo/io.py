"""Read and write zoo series.

The table readers follow base ``read.table``, ``read.csv``, ``read.csv2``,
``read.delim``, and ``read.delim2``. ``read.table.zoo`` passes ``format=""``
and ``tz=""`` through, so those arguments are present inside ``read.zoo``.
"""

from __future__ import annotations

import csv
import datetime as dt
import inspect
import math
import sys
import warnings
from pathlib import Path
from typing import Any, Callable

import numpy as np

from zoo.series import Zoo

_MISSING = object()
_ORIGIN = dt.date(1970, 1, 1)
_POSIX_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
)
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d")
_EQUAL_TOL = math.sqrt(sys.float_info.epsilon)
_RESERVED = {
    "if",
    "else",
    "repeat",
    "while",
    "function",
    "for",
    "in",
    "next",
    "break",
    "TRUE",
    "FALSE",
    "NULL",
    "Inf",
    "NaN",
    "NA",
    "NA_integer_",
    "NA_real_",
    "NA_complex_",
    "NA_character_",
    "...",
}


class DataFrame:
    """A data frame of equal-length columns, the stand-in for ``read.table``."""

    def __init__(
        self,
        names: list[str],
        columns: list[list[Any]],
        row_names: list[str] | None = None,
    ) -> None:
        self.names = [str(name) for name in names]
        self.columns = [list(column) for column in columns]
        if self.columns and len({len(column) for column in self.columns}) != 1:
            raise ValueError("columns must have the same length")
        count = len(self.columns[0]) if self.columns else 0
        if row_names is None:
            self.row_names = [str(index) for index in range(1, count + 1)]
        else:
            self.row_names = [str(name) for name in row_names]
            if self.columns and len(self.row_names) != count:
                raise ValueError("row names must have one entry per row")

    @property
    def nrow(self) -> int:
        if self.columns:
            return len(self.columns[0])
        return len(self.row_names)

    @property
    def ncol(self) -> int:
        return len(self.columns)


class TextSource:
    """In-memory text passed to a table reader, the stand-in for a text connection."""

    def __init__(self, text: str) -> None:
        self.text = "" if text is None else str(text)


class IndexList(list):
    """Several index columns, the R list that ``FUN`` receives as separate arguments."""


def _is_frame(value: Any) -> bool:
    return isinstance(value, DataFrame)


def _is_missing(value: Any) -> bool:
    return value is _MISSING


def make_names(names: list[Any], unique: bool = False, allow_: bool = True) -> list[str]:
    """R ``make.names`` for column headers."""

    fixed = [_one_name(name, allow_) for name in names]
    if unique:
        return _make_unique(fixed)
    return fixed


def _one_name(name: Any, allow_: bool) -> str:
    if name is None or (isinstance(name, float) and math.isnan(name)):
        text = "NA"
    else:
        text = str(name)
    allowed = []
    for char in text:
        if ("A" <= char <= "Z") or ("a" <= char <= "z") or ("0" <= char <= "9") or char == ".":
            allowed.append(char)
        elif allow_ and char == "_":
            allowed.append(char)
        else:
            allowed.append(".")
    cleaned = "".join(allowed)
    if cleaned == "" or cleaned[0].isdigit() or (
        cleaned[0] == "." and len(cleaned) > 1 and cleaned[1].isdigit()
    ):
        cleaned = "X" + cleaned
    if cleaned in _RESERVED:
        cleaned = cleaned + "."
    return cleaned


def _make_unique(names: list[str], sep: str = ".") -> list[str]:
    seen: dict[str, int] = {}
    used: set[str] = set()
    result = []
    for name in names:
        if name not in used:
            used.add(name)
            seen[name] = 0
            result.append(name)
            continue
        index = seen.get(name, 0)
        while True:
            index += 1
            candidate = f"{name}{sep}{index}"
            if candidate not in used:
                break
        seen[name] = index
        used.add(candidate)
        result.append(candidate)
    return result


def _read_lines(file: Any) -> list[str]:
    if isinstance(file, TextSource):
        text = file.text
    else:
        text = Path(file).read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.splitlines()


def _strip_comment(line: str, comment: str, quotes: str) -> str:
    if not comment:
        return line
    in_quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if in_quote:
            if char == in_quote:
                if index + 1 < len(line) and line[index + 1] == in_quote:
                    index += 2
                    continue
                in_quote = ""
            index += 1
            continue
        if char in quotes:
            in_quote = char
            index += 1
            continue
        if line.startswith(comment, index):
            return line[:index]
        index += 1
    return line


def _split_fields(line: str, sep: str, quotes: str) -> list[str]:
    if sep == "":
        return _split_whitespace(line, quotes)
    return next(csv.reader([line], delimiter=sep, quotechar=quotes[:1] or '"', skipinitialspace=False))


def _split_whitespace(line: str, quotes: str) -> list[str]:
    fields: list[str] = []
    index = 0
    size = len(line)
    while index < size and line[index] in " \t":
        index += 1
    while index < size:
        if line[index] in quotes:
            quote = line[index]
            index += 1
            buffer: list[str] = []
            while index < size:
                if line[index] == quote:
                    if index + 1 < size and line[index + 1] == quote:
                        buffer.append(quote)
                        index += 2
                        continue
                    index += 1
                    break
                buffer.append(line[index])
                index += 1
            fields.append("".join(buffer))
        else:
            start = index
            while index < size and line[index] not in " \t":
                index += 1
            fields.append(line[start:index])
        while index < size and line[index] in " \t":
            index += 1
    return fields


def _looks_numeric(cell: str, dec: str) -> tuple[bool, bool, float]:
    """Return whether the cell is numeric, whether it is an integer, and the value."""

    text = cell.strip() if cell == cell else cell
    if dec == ",":
        if "." in text:
            return False, False, math.nan
        text = text.replace(",", ".")
    elif dec != "." and dec in text:
        text = text.replace(dec, ".")
    if text in ("Inf", "+Inf"):
        return True, False, math.inf
    if text == "-Inf":
        return True, False, -math.inf
    if text == "NaN":
        return True, False, math.nan
    sign = ""
    body = text
    if body[:1] in "+-":
        sign = body[:1]
        body = body[1:]
    if not body:
        return False, False, math.nan
    exponent = ""
    if "e" in body.lower():
        marker = "e" if "e" in body else "E"
        coeff, _, exponent = body.partition(marker)
    else:
        coeff = body
    if exponent:
        exp_body = exponent[1:] if exponent[:1] in "+-" else exponent
        if not exp_body.isdigit():
            return False, False, math.nan
    if coeff.count(".") > 1 or not coeff.replace(".", "").isdigit() or coeff in ("", "."):
        return False, False, math.nan
    try:
        value = float(sign + coeff + (("e" + exponent) if exponent else ""))
    except ValueError:
        return False, False, math.nan
    integer = "." not in coeff and exponent == ""
    if integer:
        try:
            as_int = int(sign + coeff)
        except ValueError:
            return False, False, math.nan
        if not -2147483647 <= as_int <= 2147483647:
            integer = False
        else:
            value = float(as_int)
    return True, integer, value


def _convert_column(cells: list[str], dec: str, na_strings: list[str], kind: str | None) -> list[Any]:
    missing = set(na_strings)
    if kind in ("NULL", "null"):
        return []
    if kind in ("character", "factor"):
        return [None if cell in missing else cell for cell in cells]
    parsed: list[Any] = []
    integers = True
    numeric = True
    for cell in cells:
        if cell in missing or cell == "":
            parsed.append(None)
            continue
        ok, is_int, value = _looks_numeric(cell, dec)
        if not ok:
            numeric = False
            integers = False
            parsed.append(cell)
            continue
        integers = integers and is_int
        parsed.append(value)
    if kind in ("numeric", "double", "real"):
        return [math.nan if value is None or isinstance(value, str) else float(value) for value in parsed]
    if kind == "integer":
        out = []
        for value in parsed:
            if value is None or isinstance(value, str) or not math.isfinite(float(value)):
                out.append(None)
            else:
                out.append(int(value))
        return out
    if kind == "logical":
        mapped = {"TRUE": True, "T": True, "FALSE": False, "F": False}
        return [None if cell in missing or cell == "" else mapped.get(cell, cell) for cell in cells]
    if not numeric:
        return [None if isinstance(value, float) else value for value in parsed]
    if integers:
        return [None if value is None else int(value) for value in parsed]
    return [math.nan if value is None else float(value) for value in parsed]


def read_table(
    file: Any,
    header: bool = False,
    sep: str = "",
    quote: str = "\"'",
    dec: str = ".",
    row_names: Any = None,
    col_names: Any = None,
    na_strings: Any = "NA",
    col_classes: Any = None,
    nrows: int = -1,
    skip: int = 0,
    check_names: bool = True,
    fill: bool | None = None,
    strip_white: bool = False,
    blank_lines_skip: bool = True,
    comment_char: str = "#",
    **_ignored: Any,
) -> DataFrame:
    """The ``read.table`` pieces ``read.zoo`` uses. ``file`` may be a path or text."""

    if fill is None:
        fill = not blank_lines_skip
    if isinstance(na_strings, str):
        na_list = [na_strings]
    else:
        na_list = [str(item) for item in na_strings]
    lines = _read_lines(file)
    if skip:
        lines = lines[int(skip) :]
    records: list[list[str]] = []
    for line in lines:
        stripped = _strip_comment(line, comment_char, quote)
        if blank_lines_skip and stripped.strip() == "":
            continue
        fields = _split_fields(stripped, sep, quote)
        if strip_white:
            fields = [field.strip() for field in fields]
        records.append(fields)
        if nrows is not None and int(nrows) >= 0 and len(records) >= int(nrows) + (1 if header else 0):
            break
    if not records:
        names = list(col_names) if col_names is not None else []
        return DataFrame(names, [[] for _ in names], [])
    header_fields: list[str] | None = None
    body = records
    if header:
        header_fields = records[0]
        body = records[1:]
    width = max((len(row) for row in body), default=0)
    if header_fields is not None:
        width = max(width, len(header_fields))
    row_name_values: list[str] | None = None
    if (
        row_names is None
        and header_fields is not None
        and body
        and len(header_fields) == len(body[0]) - 1
    ):
        row_name_values = [row[0] if row else "" for row in body]
        body = [row[1:] if row else [] for row in body]
        header_fields = header_fields
        width -= 1
    elif isinstance(row_names, int) and not isinstance(row_names, bool) and row_names > 0:
        position = row_names - 1
        row_name_values = [row[position] if len(row) > position else "" for row in body]
        body = [row[:position] + row[position + 1 :] for row in body]
        if header_fields is not None and len(header_fields) > position:
            header_fields = header_fields[:position] + header_fields[position + 1 :]
        width -= 1
    if fill:
        body = [row + [""] * (width - len(row)) for row in body]
    else:
        body = [row[:width] for row in body]
    if col_names is not None:
        names = [str(name) for name in col_names]
    elif header_fields is not None:
        names = list(header_fields) + [f"V{index}" for index in range(len(header_fields) + 1, width + 1)]
        names = names[:width]
    else:
        names = [f"V{index}" for index in range(1, width + 1)]
    classes = _recycle_classes(col_classes, len(names))
    kept_names = []
    kept_cells: list[list[str]] = []
    kept_classes = []
    for index, name in enumerate(names):
        kind = classes[index] if classes else None
        if kind in ("NULL", "null"):
            continue
        kept_names.append(name)
        kept_cells.append([row[index] if index < len(row) else "" for row in body])
        kept_classes.append(kind)
    if check_names:
        kept_names = make_names(kept_names, unique=True)
    columns = [
        _convert_column(cells, dec, na_list, kind)
        for cells, kind in zip(kept_cells, kept_classes)
    ]
    if row_name_values is None:
        row_name_values = [str(index) for index in range(1, len(body) + 1)]
    return DataFrame(kept_names, columns, row_name_values)


def _recycle_classes(col_classes: Any, width: int) -> list[Any]:
    if col_classes is None:
        return [None] * width
    if isinstance(col_classes, str) or col_classes is None:
        values = [col_classes]
    else:
        values = list(col_classes)
    if not values:
        return [None] * width
    return [values[index % len(values)] for index in range(width)]


def read_csv(file: Any, header: bool = True, sep: str = ",", quote: str = '"', dec: str = ".", fill: bool = True, comment_char: str = "", **kwargs: Any) -> DataFrame:
    """``read.csv``: comma separator, header, dot decimal."""

    return read_table(file, header=header, sep=sep, quote=quote, dec=dec, fill=fill, comment_char=comment_char, **kwargs)


def read_csv2(file: Any, header: bool = True, sep: str = ";", quote: str = '"', dec: str = ",", fill: bool = True, comment_char: str = "", **kwargs: Any) -> DataFrame:
    """``read.csv2``: semicolon separator and comma decimal mark."""

    return read_table(file, header=header, sep=sep, quote=quote, dec=dec, fill=fill, comment_char=comment_char, **kwargs)


def read_delim(file: Any, header: bool = True, sep: str = "\t", quote: str = '"', dec: str = ".", fill: bool = True, comment_char: str = "", **kwargs: Any) -> DataFrame:
    """``read.delim``: tab separator and dot decimal mark."""

    return read_table(file, header=header, sep=sep, quote=quote, dec=dec, fill=fill, comment_char=comment_char, **kwargs)


def read_delim2(file: Any, header: bool = True, sep: str = "\t", quote: str = '"', dec: str = ",", fill: bool = True, comment_char: str = "", **kwargs: Any) -> DataFrame:
    """``read.delim2``: tab separator and comma decimal mark."""

    return read_table(file, header=header, sep=sep, quote=quote, dec=dec, fill=fill, comment_char=comment_char, **kwargs)


def _tzinfo(tz: str | None) -> dt.tzinfo | None:
    if tz is None or tz == "":
        return None
    if tz in ("UTC", "GMT", "Etc/UTC", "Etc/GMT"):
        return dt.timezone.utc
    from zoneinfo import ZoneInfo

    return ZoneInfo(tz)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, DataFrame):
        return value.columns
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [value.item()]
        return value.tolist()
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, list):
        return list(value)
    try:
        return list(value)
    except TypeError:
        return [value]


def _local_midnight_today() -> dt.datetime:
    today = dt.date.today()
    return dt.datetime(today.year, today.month, today.day)


def _parse_format(text: str, fmt: str) -> dt.datetime | None:
    if text is None:
        return None
    if isinstance(text, float) and math.isnan(text):
        return None
    raw = str(text).strip()
    if fmt == "":
        if raw == "" or raw == "NA":
            return None
        return _local_midnight_today()
    pattern = fmt.replace("%OS", "%S")
    try:
        return dt.datetime.strptime(raw, pattern)
    except ValueError:
        if "%S" in pattern and "." in raw:
            trimmed = pattern.replace("%S", "%S.%f")
            try:
                return dt.datetime.strptime(raw, trimmed)
            except ValueError:
                return None
        return None


def _attach_tz(value: dt.datetime | None, tz: str | None) -> dt.datetime | None:
    if value is None:
        return None
    info = _tzinfo(tz)
    if info is None:
        return value.replace(tzinfo=None)
    return value.replace(tzinfo=info)


def _try_formats(values: list[Any], formats: tuple[str, ...], tz: str | None) -> list[dt.datetime] | None:
    present = [value for value in values if not _is_na(value)]
    if not present:
        return [_attach_tz(None, tz) for _ in values]
    for fmt in formats:
        if all(_parse_format(str(value), fmt) is not None for value in present):
            return [_attach_tz(_parse_format("" if _is_na(value) else str(value), fmt) if not _is_na(value) else None, tz) for value in values]
    return None


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value == "NA":
        return False
    return False


def as_date(x: Any, format: Any = _MISSING, **_ignored: Any) -> list[dt.date | None]:
    """``as.Date`` for character, date, and numeric input."""

    values = _as_list(x)
    if values and all(isinstance(value, dt.datetime) for value in values if value is not None):
        return [None if value is None else value.date() for value in values]
    if values and all(isinstance(value, dt.date) and not isinstance(value, dt.datetime) for value in values if value is not None):
        return list(values)
    if not _is_missing(format) and format is not None:
        parsed = []
        for value in values:
            if _is_na(value):
                parsed.append(None)
                continue
            stamp = _parse_format(_format_plain(value), str(format))
            parsed.append(None if stamp is None else stamp.date())
        if any(item is None and not _is_na(value) for item, value in zip(parsed, values)):
            raise ValueError("character string is not in a standard unambiguous format")
        return parsed
    if values and all(_is_number(value) or _is_na(value) for value in values):
        out: list[dt.date | None] = []
        for value in values:
            if _is_na(value):
                out.append(None)
            else:
                out.append(_ORIGIN + dt.timedelta(days=int(value)))
        return out
    texts = [_format_plain(value) for value in values]
    found = _try_formats(texts, _DATE_FORMATS, "GMT")
    if found is None:
        raise ValueError("character string is not in a standard unambiguous format")
    return [None if value is None else value.date() for value in found]


def as_posixct(x: Any, tz: str = "", format: Any = _MISSING, **_ignored: Any) -> list[dt.datetime | None]:
    """``as.POSIXct`` for character input. An empty ``tz`` is the local zone."""

    values = _as_list(x)
    if not _is_missing(format) and format is not None:
        parsed = []
        for value in values:
            if _is_na(value):
                parsed.append(None)
                continue
            parsed.append(_attach_tz(_parse_format(_format_plain(value), str(format)), tz))
        return parsed
    if values and all(isinstance(value, dt.datetime) or _is_na(value) for value in values):
        return [_attach_tz(value, tz) if isinstance(value, dt.datetime) else None for value in values]
    texts = [_format_plain(value) for value in values]
    found = _try_formats(texts, _POSIX_FORMATS, tz)
    if found is None:
        raise ValueError("character string is not in a standard unambiguous format")
    return found


def _format_plain(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, str):
        return value
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, dt.date):
        return value.isoformat()
    if _is_number(value):
        return r_character_double(float(value))
    return str(value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool)


def _all_equal(left: list[float], right: list[float]) -> bool:
    if len(left) != len(right):
        return False
    for one, other in zip(left, right):
        if math.isnan(one) or math.isnan(other):
            return False
        scale = max(abs(one), abs(other), 1.0)
        if abs(one - other) > _EQUAL_TOL * scale:
            return False
    return True


def _hms_seconds(value: dt.datetime) -> float:
    return value.second + 60 * value.minute + 3600 * value.hour + value.microsecond / 1_000_000


def _to_default(x: Any, **_ignored: Any) -> Any:
    values = _as_list(x)
    try:
        posix = as_posixct(values, tz="")
    except (ValueError, TypeError):
        posix = None
    if posix is not None and not any(item is None and not _is_na(value) for item, value in zip(posix, values)):
        stamps = [item for item in posix if item is not None]
        if stamps:
            seconds = [_hms_seconds(item) for item in stamps]
            if _all_equal(seconds, [seconds[0]] * len(seconds)):
                try:
                    return as_date(values)
                except (ValueError, TypeError):
                    return posix
        return posix
    try:
        return as_date(values)
    except (ValueError, TypeError):
        return [None] * len(values)


def _to_numeric(x: Any, **_ignored: Any) -> Any:
    return x


def _make_to_date(format_missing: bool, format_value: Any) -> Callable[..., Any]:
    if format_missing or format_value is None:
        return lambda x, **kwargs: as_date(x)

    def _to_date(x: Any, format: Any = format_value, **_kwargs: Any) -> Any:
        text = "" if format is None else str(format)
        if any(token in text for token in ("%H", "%M", "%S")):
            warnings.warn(
                "the 'format' appears to be for a date/time, please specify 'tz' if you want to create a POSIXct time index",
                stacklevel=2,
            )
        return as_date(x, format=format)

    return _to_date


def _make_to_posixct(format_missing: bool, format_value: Any) -> Callable[..., Any]:
    if format_missing or format_value is None:
        return lambda x, tz="", **kwargs: as_posixct(x, tz=tz)

    def _to_posixct(x: Any, format: Any = format_value, tz: str = "", **_kwargs: Any) -> Any:
        texts = [_format_plain(value) for value in _as_list(x)]
        return [
            None if _is_na(value) else _attach_tz(_parse_format(text, "" if format is None else str(format)), tz)
            for value, text in zip(_as_list(x), texts)
        ]

    return _to_posixct


def paste(*parts: Any, sep: str = " ", collapse: Any = None, recycle0: bool = False) -> Any:
    """R ``paste`` with the default space separator."""

    columns = [_as_list(part) for part in parts]
    if not columns:
        return []
    if recycle0 and any(len(column) == 0 for column in columns):
        return []
    width = max(len(column) for column in columns)
    if width == 0:
        return []
    rows = []
    for index in range(width):
        bits = []
        for column in columns:
            if not column:
                bits.append("")
            else:
                item = column[index % len(column)]
                bits.append("NA" if item is None else str(item))
        rows.append(sep.join(bits))
    if collapse is not None:
        return str(collapse).join(rows)
    return rows


def _n_formals(fun: Callable[..., Any]) -> int:
    try:
        signature = inspect.signature(fun)
    except (TypeError, ValueError):
        return 0
    return len(signature.parameters)


def _match_fun(fun: Any) -> Callable[..., Any]:
    if fun is None:
        raise ValueError("FUN is missing")
    if callable(fun) and not isinstance(fun, str):
        return fun
    name = str(fun)
    known = {
        "as.Date": as_date,
        "as.POSIXct": as_posixct,
        "as.numeric": _as_numeric,
        "identity": _identity,
        "paste": paste,
        "mean": _mean,
        "sum": _sum,
        "format": r_format,
    }
    if name not in known:
        raise ValueError(f"object '{name}' of mode 'function' was not found")
    return known[name]


def _identity(x: Any, **_kwargs: Any) -> Any:
    return x


def _as_numeric(x: Any, **_kwargs: Any) -> list[float]:
    return [math.nan if _is_na(value) else float(value) for value in _as_list(x)]


def _mean(x: Any, **_kwargs: Any) -> float:
    values = [float(value) for value in np.asarray(x, dtype=float).reshape(-1) if not math.isnan(float(value))]
    if not values:
        return math.nan
    return float(sum(values) / len(values))


def _sum(x: Any, **_kwargs: Any) -> float:
    values = [float(value) for value in np.asarray(x, dtype=float).reshape(-1)]
    return float(sum(values))


def _atomic_as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        if any(isinstance(item, (list, tuple, np.ndarray)) for item in value):
            return value
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, np.ndarray) and value.ndim > 0:
        return value.tolist()
    return [value]


def _is_scalar_one(value: Any) -> bool:
    return _is_number(value) and float(value) == 1.0 and float(value).is_integer()


def _prepare_index_column(index_column: Any, fun: Any, fun2: Any) -> Any:
    matched = None if fun is None else _match_fun(fun)
    matched2 = None if fun2 is None else _match_fun(fun2)
    convert = False
    if fun is None and fun2 is None:
        convert = True
    elif matched is paste or fun == "paste":
        convert = True
    elif fun is None and (matched2 is paste or fun2 == "paste"):
        convert = True
    elif fun is not None and not isinstance(index_column, list) and _length(index_column) <= _n_formals(matched):
        convert = True
    elif fun is None and fun2 is not None and _length(index_column) <= _n_formals(matched2):
        convert = True
    if convert:
        index_column = _atomic_as_list(index_column)
    if (
        isinstance(index_column, list)
        and len(index_column) == 1
        and _is_scalar_one(index_column[0])
    ):
        return index_column[0]
    return index_column


def _length(value: Any) -> int:
    if isinstance(value, (str, bytes)):
        return 1
    if isinstance(value, np.ndarray):
        return int(value.size) if value.ndim > 0 else 1
    try:
        return len(value)
    except TypeError:
        return 1


def _flatten_index_spec(index_column: Any) -> list[Any]:
    if isinstance(index_column, list):
        flat: list[Any] = []
        for item in index_column:
            if isinstance(item, (list, tuple, np.ndarray)):
                flat.extend(_as_list(item))
            else:
                flat.append(item)
        return flat
    if isinstance(index_column, (tuple, np.ndarray)):
        return _as_list(index_column)
    return [index_column]


def _name_to_num(value: Any, names: list[str]) -> Any:
    if isinstance(value, str):
        try:
            return names.index(value) + 1
        except ValueError:
            return 0
    if isinstance(value, (list, tuple)):
        return [_name_to_num(item, names) for item in value]
    if isinstance(value, np.ndarray):
        return [_name_to_num(item, names) for item in value.tolist()]
    return value


def _single_index_position(index_column: Any, ncol: int) -> int | None:
    if isinstance(index_column, (list, str)) or not _is_number(index_column):
        return None
    if _zero_index(index_column):
        return None
    position = int(index_column)
    if position < 1 or position > ncol:
        return None
    return position


def _zero_index(index_column: Any) -> bool:
    if isinstance(index_column, list):
        return len(index_column) == 1 and _zero_index(index_column[0])
    return _is_number(index_column) and float(index_column) == 0.0


def _column_mask(index_column: Any, names: list[str]) -> list[bool]:
    flat = _flatten_index_spec(index_column)
    numeric = all(_is_number(item) or item == 0 for item in flat)
    mask = []
    positions = {int(item) for item in flat if _is_number(item)}
    labels = {str(item) for item in flat if isinstance(item, str)}
    for index, name in enumerate(names, start=1):
        if numeric:
            mask.append(index in positions)
        else:
            mask.append(index in positions or name in labels or name in {str(item) for item in flat})
    return mask


def _take_column(frame: DataFrame, spec: Any) -> Any:
    if isinstance(spec, (list, tuple)):
        numbers = [int(item) for item in spec]
        if len(numbers) == 1:
            return list(frame.columns[numbers[0] - 1])
        return DataFrame(
            [frame.names[number - 1] for number in numbers],
            [list(frame.columns[number - 1]) for number in numbers],
            frame.row_names,
        )
    return list(frame.columns[int(spec) - 1])


def _extract_index(frame: DataFrame, index_column: Any) -> Any:
    if _zero_index(index_column):
        return list(frame.row_names)
    if isinstance(index_column, list):
        return IndexList(_take_column(frame, spec) for spec in index_column)
    return _take_column(frame, index_column)


def _numeric_column(column: list[Any]) -> bool:
    if not column:
        return False
    return all(_is_number(value) or _is_na(value) for value in column)


def _character_column(column: list[Any]) -> bool:
    return any(isinstance(value, str) for value in column)


def _matrix_from_frame(frame: DataFrame, drop: bool) -> tuple[np.ndarray, list[str] | None]:
    if frame.ncol == 0:
        return np.empty((frame.nrow, 0), dtype=float, order="F"), []
    columns = []
    for column in frame.columns:
        if _numeric_column(column) or all(_is_na(value) or _is_number(value) for value in column):
            columns.append([math.nan if _is_na(value) else float(value) for value in column])
        else:
            columns.append(column)
    if any(isinstance(column[0], str) for column in columns if column):
        width = len(columns)
        data = np.empty((frame.nrow, width), dtype=object, order="F")
        for col_index, column in enumerate(columns):
            data[:, col_index] = column
        names = list(frame.names)
        if width == 1 and drop:
            return np.asarray(data[:, 0], dtype=object), None
        return data, names
    stacked = np.column_stack(columns) if len(columns) > 1 else np.asarray(columns[0], dtype=float).reshape(-1, 1)
    data = np.array(stacked, dtype=float, order="F")
    names = list(frame.names)
    if data.shape[1] == 1 and drop:
        return np.asarray(data[:, 0], dtype=float).copy(), None
    return data, names


def _index_array(index: Any) -> Any:
    if isinstance(index, list) and index and all(isinstance(value, dt.datetime) or value is None for value in index):
        return np.array(index, dtype=object)
    if isinstance(index, list) and index and all(
        isinstance(value, dt.date) and not isinstance(value, dt.datetime) or value is None for value in index
    ):
        return np.array(index, dtype=object)
    if isinstance(index, list) and index and all(_is_number(value) or _is_na(value) for value in index):
        if all(isinstance(value, (int, np.integer)) and not isinstance(value, bool) or _is_na(value) for value in index):
            if any(_is_na(value) for value in index):
                return np.array([math.nan if _is_na(value) else int(value) for value in index], dtype=float)
            return np.array([int(value) for value in index], dtype=int)
        return np.array([math.nan if _is_na(value) else float(value) for value in index], dtype=float)
    if isinstance(index, list):
        return np.array(index, dtype=object)
    return index


def _bad_rows(index: Any) -> list[int]:
    values = index.tolist() if isinstance(index, np.ndarray) else list(index)
    rows = []
    for position, value in enumerate(values, start=1):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            rows.append(position)
    return rows


def _stop_bad_index(rows: list[int]) -> None:
    if len(rows) == 1:
        message = f"index has bad entry at data row {rows[0]}"
    elif len(rows) <= 100:
        message = "index has bad entries at data rows: " + " ".join(str(row) for row in rows)
    else:
        head = " ".join(str(row) for row in rows[:100])
        message = f"index has {len(rows)} bad entries at data rows: {head} ..."
    raise ValueError(message)


def _call_index_fun(fun: Callable[..., Any], index: Any, extras: dict[str, Any], fun0: Callable[..., Any] | None) -> Any:
    if _is_frame(index):
        return fun(index, **extras)
    if isinstance(index, IndexList):
        if fun0 is None:
            return fun(*index, **extras)
        pasted = fun0(*index)
        return fun(pasted, **extras)
    return fun(index, **extras)


def _numeric_index_values(index: Any) -> np.ndarray:
    values = index.tolist() if isinstance(index, np.ndarray) else list(index)
    out = []
    for value in values:
        if isinstance(value, dt.datetime):
            out.append(value.timestamp())
        elif isinstance(value, dt.date):
            out.append(float((value - _ORIGIN).days))
        elif _is_na(value):
            out.append(math.nan)
        else:
            out.append(float(value))
    return np.asarray(out, dtype=float)


def _is_regular(index: Any) -> bool:
    values = _numeric_index_values(index)
    if values.size < 2 or np.isnan(values).any():
        return False
    diffs = np.diff(values)
    if np.any(diffs <= 0):
        return False
    return bool(np.allclose(diffs, diffs[0], rtol=0.0, atol=1e-8))


def _frequency(index: Any) -> float | None:
    values = _numeric_index_values(index)
    if values.size < 2:
        return 1.0
    step = float(values[1] - values[0])
    if step == 0:
        return None
    return 1.0 / step


def _group_rows(index: Any) -> list[tuple[Any, list[int]]]:
    values = index.tolist() if isinstance(index, np.ndarray) else list(index)
    groups: dict[Any, list[int]] = {}
    order: list[Any] = []
    for position, value in enumerate(values):
        key = value.isoformat() if isinstance(value, dt.date) and not isinstance(value, dt.datetime) else value
        if isinstance(value, dt.datetime):
            key = value.timestamp()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(position)
    paired = [(key, groups[key]) for key in order]
    paired.sort(key=lambda item: _sort_key(values[item[1][0]]))
    return paired


def _sort_key(value: Any) -> tuple[int, float]:
    if isinstance(value, dt.datetime):
        return (0, value.timestamp())
    if isinstance(value, dt.date):
        return (0, float((value - _ORIGIN).days))
    if _is_number(value):
        return (0, float(value))
    return (1, 0.0)


def _aggregate_zoo(data: np.ndarray, index: Any, fun: Callable[..., Any]) -> Zoo:
    groups = _group_rows(index)
    index_values = index.tolist() if isinstance(index, np.ndarray) else list(index)
    new_index = [index_values[rows[0]] for _key, rows in groups]
    if data.ndim == 1:
        reduced = [fun(data[rows]) for _key, rows in groups]
        result_data = np.asarray(reduced, dtype=float)
    else:
        reduced_cols = []
        for column in range(data.shape[1]):
            reduced_cols.append([fun(data[rows, column]) for _key, rows in groups])
        result_data = np.array(reduced_cols, dtype=float, order="F").T
    zoo = Zoo(result_data, _index_array(new_index))
    return zoo


def _split_labels(index: Any, split: Any, frame: DataFrame) -> Any:
    if isinstance(split, str):
        position = frame.names.index(split) + 1 if split in frame.names else 0
    else:
        position = split
    if _is_number(position) and math.isfinite(float(position)):
        return list(frame.columns[int(position) - 1])
    values = index if not isinstance(index, list) else index
    keys = values.tolist() if isinstance(values, np.ndarray) else list(values)
    if split == math.inf or split == float("inf"):
        counts: dict[Any, int] = {}
        labels = []
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
            labels.append(counts[key])
        return labels
    if split == -math.inf or split == float("-inf"):
        totals: dict[Any, int] = {}
        for key in keys:
            totals[key] = totals.get(key, 0) + 1
        seen: dict[Any, int] = {}
        labels = []
        for key in keys:
            seen[key] = seen.get(key, 0) + 1
            labels.append(totals[key] - seen[key] + 1)
        return labels
    return keys


def _subset_rows(data: np.ndarray, rows: list[int]) -> np.ndarray:
    if data.ndim == 1:
        return data[rows]
    return data[rows, :]


def _merge_zoo(parts: list[Zoo]) -> Zoo:
    if not parts:
        return Zoo(np.empty((0, 0), dtype=float), np.array([], dtype=float))
    if len(parts) == 1:
        return parts[0]
    keys: list[tuple[tuple[int, float], Any]] = []
    seen: set[Any] = set()
    for part in parts:
        values = part.index.tolist() if isinstance(part.index, np.ndarray) else list(part.index)
        for value in values:
            marker = value.timestamp() if isinstance(value, dt.datetime) else value.isoformat() if isinstance(value, dt.date) else value
            if marker not in seen:
                seen.add(marker)
                keys.append((_sort_key(value), value))
    keys.sort(key=lambda item: item[0])
    ordered = [value for _key, value in keys]
    blocks = []
    names: list[str] = []
    for part_index, part in enumerate(parts):
        lookup = {}
        values = part.index.tolist() if isinstance(part.index, np.ndarray) else list(part.index)
        data = np.asarray(part.data)
        for row, value in enumerate(values):
            marker = value.timestamp() if isinstance(value, dt.datetime) else value.isoformat() if isinstance(value, dt.date) else value
            lookup[marker] = row
        if data.ndim == 1:
            column = []
            for value in ordered:
                marker = value.timestamp() if isinstance(value, dt.datetime) else value.isoformat() if isinstance(value, dt.date) else value
                column.append(math.nan if marker not in lookup else float(data[lookup[marker]]))
            blocks.append(column)
            label = None if part.columns is None else (part.columns[0] if part.columns else None)
            names.append(label or f"V{part_index + 1}")
        else:
            labels = list(part.columns) if part.columns is not None else [f"V{col + 1}" for col in range(data.shape[1])]
            for col, label in enumerate(labels):
                column = []
                for value in ordered:
                    marker = value.timestamp() if isinstance(value, dt.datetime) else value.isoformat() if isinstance(value, dt.date) else value
                    column.append(math.nan if marker not in lookup else float(data[lookup[marker], col]))
                blocks.append(column)
                names.append(str(label))
    names = _make_unique(names)
    matrix = np.array(blocks, dtype=float, order="F").T if blocks else np.empty((len(ordered), 0), dtype=float)
    zoo = Zoo(matrix, _index_array(ordered))
    zoo.columns = names
    return zoo


def _build_zoo(data: np.ndarray, index: Any, names: list[str] | None, regular: bool, aggregate: Any) -> Zoo:
    rows = _bad_rows(index)
    if rows:
        _stop_bad_index(rows)
    if _nrow(data) != _length(index):
        raise ValueError("index does not match data")
    agg_fun = None
    if aggregate is True:
        agg_fun = _mean
    elif aggregate is False or aggregate is None:
        agg_fun = None
    else:
        agg_fun = _match_fun(aggregate)
        if not callable(agg_fun):
            raise ValueError("invalid specification of 'aggregate'")
    if agg_fun is not None:
        zoo = _aggregate_zoo(data, index, agg_fun)
    else:
        zoo = Zoo(data, index)
    if names is not None and np.asarray(zoo.data).ndim == 2:
        zoo.columns = names
    else:
        zoo.columns = None
    if regular and _is_regular(zoo.index):
        rebuilt = Zoo(zoo.data, zoo.index, frequency=_frequency(zoo.index), regular=True)
        rebuilt.columns = zoo.columns
        return rebuilt
    zoo.regular = False
    zoo.frequency = None
    return zoo


def _nrow(data: np.ndarray) -> int:
    array = np.asarray(data)
    if array.ndim == 0:
        return 1
    return int(array.shape[0])


def read_zoo(
    file: Any = _MISSING,
    format: Any = _MISSING,
    tz: Any = _MISSING,
    FUN: Any = None,
    regular: bool = False,
    index_column: Any = 1,
    drop: bool = True,
    FUN2: Any = None,
    split: Any = None,
    aggregate: Any = False,
    *args: Any,
    text: Any = _MISSING,
    read: Any = None,
    **kwargs: Any,
) -> Zoo:
    """Read a table and return a :class:`Zoo` series.

    ``format`` and ``tz`` default to an empty string, and a caller that omits
    them is recorded as missing. ``read.table.zoo`` supplies both, so the
    index goes through ``strptime`` with an empty format.
    """

    if args:
        raise TypeError("positional arguments after aggregate are not used; pass text= and read= by name")
    if _is_missing(file) and not _is_missing(text):
        file = TextSource(text if isinstance(text, str) else "\n".join(str(line) for line in text))
    if _is_missing(file):
        raise TypeError("argument \"file\" is missing, with no default")
    if isinstance(file, (list, tuple)) and all(isinstance(item, (str, Path)) for item in file) and len(file) > 1:
        parts = [
            read_zoo(
                item,
                format=format,
                tz=tz,
                FUN=FUN,
                regular=regular,
                index_column=index_column,
                drop=drop,
                FUN2=FUN2,
                split=split,
                aggregate=aggregate,
                read=read,
                **kwargs,
            )
            for item in file
        ]
        return _merge_zoo(parts)
    reader = read_table if read is None else read
    if _is_frame(file):
        frame = file
    else:
        frame = reader(file, **kwargs)
        if not _is_frame(frame):
            frame = _frame_from_mapping(frame)
    format_missing = _is_missing(format)
    tz_missing = _is_missing(tz)
    position = _single_index_position(index_column, frame.ncol)
    if (
        _is_frame(file)
        and position is not None
        and not _character_column(frame.columns[position - 1])
        and tz_missing
        and format_missing
        and FUN is None
    ):
        FUN = _identity
    index_column = _prepare_index_column(index_column, FUN, FUN2)
    if isinstance(index_column, list):
        index_column = [_name_to_num(item, frame.names) for item in index_column]
    else:
        index_column = _name_to_num(index_column, frame.names)
    mask = _column_mask(index_column, frame.names) if not _zero_index(index_column) else [False] * frame.ncol
    if frame.nrow < 1:
        kept = DataFrame(
            [name for name, keep in zip(frame.names, mask) if not keep],
            [column for column, keep in zip(frame.columns, mask) if not keep],
            frame.row_names,
        )
        data, names = _matrix_from_frame(kept, drop)
        zoo = Zoo(data, np.array([], dtype=float))
        zoo.columns = names if data.ndim == 2 else None
        return zoo
    if frame.ncol < 1 and not _zero_index(index_column):
        raise ValueError("data file must specify at least one column")
    index = _extract_index(frame, index_column)
    split_position = split
    if isinstance(split, str):
        split_position = frame.names.index(split) + 1 if split in frame.names else 0
    drop_positions = set()
    if not _zero_index(index_column):
        for position, keep in enumerate(mask, start=1):
            if keep:
                drop_positions.add(position)
    if split is not None:
        if _is_number(split_position) and math.isfinite(float(split_position)) and int(split_position) == 0:
            raise ValueError("split: " + str(split) + " not found in colnames: " + " ".join(frame.names))
        if _is_number(split_position) and math.isfinite(float(split_position)):
            drop_positions.add(int(split_position))
    kept_columns = []
    kept_names = []
    for position, (name, column) in enumerate(zip(frame.names, frame.columns), start=1):
        if position in drop_positions:
            continue
        kept_columns.append(column)
        kept_names.append(name)
    kept = DataFrame(kept_names, kept_columns, frame.row_names)
    data, names = _matrix_from_frame(kept, drop)
    to_date = _make_to_date(format_missing, None if format_missing else format)
    to_posixct = _make_to_posixct(format_missing, None if format_missing else format)
    fun0 = None
    if FUN is None and FUN2 is not None:
        FUN = FUN2
        FUN2 = None
    if FUN is None:
        if isinstance(index_column, list):
            fun0 = paste
        single = index if not isinstance(index, list) else None
        if not tz_missing and tz is not None:
            FUN = to_posixct
        elif not format_missing and format is not None:
            FUN = to_date
        elif single is not None and _numeric_column(_as_list(single)):
            FUN = _to_numeric
        else:
            FUN = _to_default
    fun = _match_fun(FUN) if not callable(FUN) else FUN
    extras: dict[str, Any] = {}
    if not format_missing and format is not None:
        extras["format"] = format
    if not tz_missing and tz is not None:
        extras["tz"] = tz
    index = _call_index_fun(fun, index, extras, fun0)
    if FUN2 is not None:
        index = _match_fun(FUN2)(index)
    index = _index_array(index)
    if split is None:
        return _build_zoo(data, index, names, regular, aggregate)
    labels = _split_labels(index, split if not isinstance(split, str) else split_position, frame)
    label_values = list(labels)
    groups: dict[Any, list[int]] = {}
    order: list[Any] = []
    for position, label in enumerate(label_values):
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(position)
    parts = []
    index_values = index.tolist() if isinstance(index, np.ndarray) else list(index)
    for label in order:
        rows = groups[label]
        piece_index = _index_array([index_values[row] for row in rows])
        piece_data = _subset_rows(data, rows)
        piece = _build_zoo(piece_data, piece_index, names, regular, aggregate)
        piece.columns = [f"{label}.{name}" if name else str(label) for name in (piece.columns or [])] if piece.columns else [str(label)]
        if np.asarray(piece.data).ndim == 1:
            piece.columns = [str(label)]
        parts.append(piece)
    return _merge_zoo(parts)


def _frame_from_mapping(value: Any) -> DataFrame:
    if isinstance(value, dict):
        names = [str(key) for key in value]
        columns = [list(value[key]) for key in value]
        return DataFrame(names, columns)
    raise TypeError("read() must return a data frame")


def read_table_zoo(
    file: Any,
    format: Any = "",
    tz: Any = "",
    FUN: Any = None,
    regular: bool = False,
    index_column: Any = 1,
    drop: bool = True,
    FUN2: Any = None,
    split: Any = None,
    aggregate: Any = False,
    **kwargs: Any,
) -> Zoo:
    """Read with ``read.table``, then ``read.zoo``.

    ``format`` and ``tz`` are always forwarded, including their empty defaults.
    """

    frame = read_table(file, **kwargs)
    return read_zoo(
        frame,
        format=format,
        tz=tz,
        FUN=FUN,
        regular=regular,
        index_column=index_column,
        drop=drop,
        FUN2=FUN2,
        split=split,
        aggregate=aggregate,
    )


def read_csv_zoo(*args: Any, read: Any = None, **kwargs: Any) -> Zoo:
    """``read.zoo`` with ``read.csv``."""

    reader = read_csv if read is None else read
    return read_zoo(*args, read=reader, **kwargs)


def read_csv2_zoo(*args: Any, read: Any = None, **kwargs: Any) -> Zoo:
    """``read.zoo`` with ``read.csv2`` (semicolon, comma decimal)."""

    reader = read_csv2 if read is None else read
    return read_zoo(*args, read=reader, **kwargs)


def read_delim_zoo(*args: Any, read: Any = None, **kwargs: Any) -> Zoo:
    """``read.zoo`` with ``read.delim``."""

    reader = read_delim if read is None else read
    return read_zoo(*args, read=reader, **kwargs)


def read_delim2_zoo(*args: Any, read: Any = None, **kwargs: Any) -> Zoo:
    """``read.zoo`` with ``read.delim2`` (tab, comma decimal)."""

    reader = read_delim2 if read is None else read
    return read_zoo(*args, read=reader, **kwargs)


def r_character_double(value: float) -> str:
    """R ``as.character`` for a double: 15 digits, scientific when it is shorter."""

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def r_format(x: Any, **_kwargs: Any) -> list[str]:
    """R ``format`` for the index written by ``write.zoo``."""

    values = x.tolist() if isinstance(x, np.ndarray) else list(x) if not isinstance(x, (str, bytes)) else [x]
    if not values:
        return []
    sample = next((value for value in values if value is not None and not (isinstance(value, float) and math.isnan(value))), None)
    if isinstance(sample, dt.datetime):
        midnight = all(isinstance(value, dt.datetime) and value.hour == value.minute == value.second == value.microsecond == 0 for value in values if isinstance(value, dt.datetime))
        formatted = []
        for value in values:
            if not isinstance(value, dt.datetime):
                formatted.append("NA")
            elif midnight:
                formatted.append(value.strftime("%Y-%m-%d"))
            else:
                formatted.append(value.strftime("%Y-%m-%d %H:%M:%S"))
        return formatted
    if isinstance(sample, dt.date):
        return ["NA" if not isinstance(value, dt.date) else value.isoformat() for value in values]
    numbers = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            numbers.append(None)
        else:
            numbers.append(float(value))
    return _format_numeric(numbers)


def _format_numeric(values: list[float | None]) -> list[str]:
    present = [value for value in values if value is not None and not math.isnan(value)]
    if not present:
        return ["NA" for _ in values]
    if all(math.isfinite(value) and float(value).is_integer() and abs(value) < 1e7 for value in present):
        texts = []
        for value in values:
            if value is None or math.isnan(value):
                texts.append("NA")
            else:
                texts.append(str(int(value)))
        width = max(len(text) for text in texts)
        return [text.rjust(width) for text in texts]
    texts = ["NA" if value is None or math.isnan(value) else r_character_double(value) for value in values]
    width = max(len(text) for text in texts)
    return [text.rjust(width) for text in texts]


def _quote_text(value: str, qmethod: str) -> str:
    if qmethod == "double":
        return '"' + value.replace('"', '""') + '"'
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _write_cell(value: Any, na: str, dec: str, quote: bool, qmethod: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return na
    if isinstance(value, str):
        return _quote_text(value, qmethod) if quote else value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    number = float(value)
    if math.isnan(number):
        return na
    text = r_character_double(number)
    if dec != ".":
        text = text.replace(".", dec)
    return text


def write_table(
    columns: list[list[Any]],
    names: list[str],
    file: Any = "",
    row_names: Any = False,
    col_names: Any = True,
    sep: str = " ",
    eol: str = "\n",
    na: str = "NA",
    dec: str = ".",
    quote: Any = True,
    append: bool = False,
    qmethod: str = "escape",
) -> None:
    """``write.table`` for a data frame whose first column may be the index."""

    if qmethod not in ("escape", "double"):
        raise ValueError("'qmethod' should be one of 'escape', 'double'")
    width = len(names)
    count = len(columns[0]) if columns else 0
    quote_columns = set(range(width)) if quote is True else set()
    if isinstance(quote, (list, tuple)):
        quote_columns = {int(item) - 1 for item in quote}
    lines: list[str] = []
    if col_names:
        header = []
        for name in names:
            if quote is True or quote is None:
                header.append(_quote_text(str(name), qmethod))
            else:
                header.append(str(name))
        lines.append(sep.join(header))
    row_name_values: list[str] | None = None
    if row_names is True:
        row_name_values = [str(index) for index in range(1, count + 1)]
    elif isinstance(row_names, (list, tuple)):
        row_name_values = [str(item) for item in row_names]
    for row in range(count):
        cells = []
        if row_name_values is not None:
            cells.append(_quote_text(row_name_values[row], qmethod) if quote else row_name_values[row])
        for column in range(width):
            cells.append(
                _write_cell(
                    columns[column][row],
                    na,
                    dec,
                    column in quote_columns and isinstance(columns[column][row], str),
                    qmethod,
                )
            )
        lines.append(sep.join(cells))
    payload = eol.join(lines) + (eol if lines else "")
    if file == "" or file is None:
        sys.stdout.write(payload)
        return
    mode = "a" if append else "w"
    with open(file, mode, encoding="utf-8", newline="") as handle:
        handle.write(payload)


def write_zoo(
    x: Zoo,
    file: Any = "",
    index_name: str = "Index",
    row_names: bool = False,
    col_names: Any = None,
    FUN: Any = None,
    **kwargs: Any,
) -> None:
    """Write a zoo series with the index in the first column.

    The index is formatted with ``FUN`` (``format`` by default) and the table
    is written by ``write.table``.
    """

    data = np.asarray(x.data)
    if data.ndim == 0:
        data = data.reshape(1)
    if data.ndim == 1:
        columns = [data.tolist()]
        names = ["V1"]
        has_names = False
    else:
        columns = [data[:, column].tolist() for column in range(data.shape[1])]
        stored = getattr(x, "columns", None)
        if stored:
            names = [str(name) for name in stored]
            has_names = True
        else:
            names = [f"V{column + 1}" for column in range(data.shape[1])]
            has_names = False
    if col_names is None:
        col_names = has_names
    if any(name == index_name for name in names):
        raise ValueError(f"all(names(dx) != {index_name!r}) is not TRUE")
    formatter = r_format if FUN is None else _match_fun(FUN)
    labels = formatter(x.index)
    if isinstance(labels, str):
        labels = [labels]
    labels = [str(label) for label in labels]
    columns.append(labels)
    names.append(index_name)
    ordered = [columns[-1]] + columns[:-1]
    ordered_names = [names[-1]] + names[:-1]
    quote = kwargs.pop("quote", True)
    write_table(
        ordered,
        ordered_names,
        file=file,
        row_names=row_names,
        col_names=col_names,
        quote=quote,
        **kwargs,
    )
