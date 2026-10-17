"""Write data frames the way readr writes delimited text."""

from __future__ import annotations

import bz2
import gzip
import lzma
import math
from datetime import date, datetime, timezone
from pathlib import Path

from readr.parse import Factor, Hms


def format_double(value) -> str:
    """Shortest decimal that matches vroom's grisu3 for ordinary values."""
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    text = format(float(value), ".16g")
    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e")
        text = f"{mantissa}e{int(exponent)}"
    return text


def _cell(value, na: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, Hms):
        return str(value)
    if isinstance(value, datetime):
        utc = value.astimezone(timezone.utc)
        if utc.microsecond:
            return utc.strftime("%Y-%m-%dT%H:%M:%S.%f").rstrip("0") + "Z"
        return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return format_double(value)
    return str(value)


def _value_kind(value) -> str:
    if value is None:
        return "missing"
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, (int, float)):
        return "number"
    return "character"


def _quote_field(text: str | None, delim: str, quote: str, escape: str, na: str, mode: str, kind: str = "character") -> str:
    if text is None:
        return na
    if mode == "none":
        return text
    # quote = "all" quotes names and character fields. Numbers, logicals, and NA stay bare.
    if mode == "all":
        must = kind in ("name", "character")
    else:
        must = text == na or any(piece in text for piece in (delim, quote, "\n", "\r"))
    if escape == "double":
        escaped = text.replace(quote, quote * 2) if quote else text
    elif escape == "backslash":
        escaped = (
            text.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        if quote:
            escaped = escaped.replace(quote, "\\" + quote)
    else:
        escaped = text
    if must and quote:
        return quote + escaped + quote
    return escaped


def _frame_columns(x):
    names = list(getattr(x, "names"))
    columns = []
    for column in x.columns:
        if isinstance(column, Factor):
            columns.append(list(column.values))
        else:
            columns.append(list(column))
    return names, columns, x.nrow


def format_delim(x, delim=" ", na="NA", col_names=True, quote="needed", escape="double", eol="\n"):
    """Render a data frame as delimited text."""
    if not hasattr(x, "names") or not hasattr(x, "columns"):
        raise TypeError("x must be a data frame")
    for column in x.columns:
        if column and isinstance(column[0], (list, dict)):
            raise ValueError("`x` must not contain list or matrix columns")
    quote_mode = quote if isinstance(quote, str) else "needed"
    escape_mode = {"double": "double", "backslash": "backslash", "none": "none"}.get(
        escape if isinstance(escape, str) else "double", "double"
    )
    names, columns, nrow = _frame_columns(x)
    lines = []
    if col_names:
        lines.append(
            delim.join(
                _quote_field(name, delim, '"', escape_mode, na, quote_mode, "name") for name in names
            )
        )
    for row in range(nrow):
        cells = []
        for column in columns:
            value = column[row]
            cells.append(
                _quote_field(_cell(value, na), delim, '"', escape_mode, na, quote_mode, _value_kind(value))
            )
        lines.append(delim.join(cells))
    return eol.join(lines) + (eol if lines else "")


def _open_out(file, append: bool, bom: bool):
    path = str(file)
    mode = "ab" if append else "wb"
    if path.endswith(".gz"):
        handle = gzip.open(path, mode)
    elif path.endswith(".bz2"):
        handle = bz2.open(path, mode)
    elif path.endswith(".xz"):
        handle = lzma.open(path, mode)
    else:
        handle = open(path, mode)
    if bom and not append:
        handle.write(b"\xef\xbb\xbf")
    return handle


def write_delim(x, file, delim=" ", na="NA", append=False, col_names=None, quote="needed", escape="double", eol="\n", num_threads=None, progress=None):
    """Write a data frame. `x` is returned."""
    if col_names is None:
        col_names = not append
    payload = format_delim(x, delim, na, col_names, quote, escape, eol)
    if file is None or file == "":
        return payload
    with _open_out(file, append, bom=False) as handle:
        handle.write(payload.encode("utf-8"))
    return x


def write_csv(x, file, na="NA", append=False, col_names=None, quote="needed", escape="double", eol="\n", num_threads=None, progress=None):
    return write_delim(x, file, ",", na, append, col_names, quote, escape, eol, num_threads, progress)


def write_csv2(x, file, na="NA", append=False, col_names=None, quote="needed", escape="double", eol="\n", num_threads=None, progress=None):
    changed = _comma_decimals(x)
    return write_delim(changed, file, ";", na, append, col_names, quote, escape, eol, num_threads, progress)


def write_tsv(x, file, na="NA", append=False, col_names=None, quote="none", escape="double", eol="\n", num_threads=None, progress=None):
    return write_delim(x, file, "\t", na, append, col_names, quote, escape, eol, num_threads, progress)


def _excel_datetimes(x):
    from readr.read import Table

    columns = []
    for column in x.columns:
        converted = []
        for value in column:
            if isinstance(value, datetime):
                converted.append(value.strftime("%Y/%m/%d %H:%M:%S"))
            else:
                converted.append(value)
        columns.append(converted)
    return Table(list(x.names), columns, x.nrow)


def write_excel_csv(x, file, na="NA", append=False, col_names=None, delim=",", quote="all", escape="double", eol="\n"):
    if col_names is None:
        col_names = not append
    payload = format_delim(_excel_datetimes(x), delim, na, col_names, quote, escape, eol)
    with _open_out(file, append, bom=True) as handle:
        handle.write(payload.encode("utf-8"))
    return x


def write_excel_csv2(x, file, na="NA", append=False, col_names=None, delim=";", quote="all", escape="double", eol="\n"):
    return write_excel_csv(_comma_decimals(x), file, na, append, col_names, delim, quote, escape, eol)


def format_csv(x, na="NA", append=False, col_names=True, quote="needed", escape="double", eol="\n"):
    return format_delim(x, ",", na, col_names, quote, escape, eol)


def format_csv2(x, na="NA", append=False, col_names=True, quote="needed", escape="double", eol="\n"):
    return format_delim(_comma_decimals(x), ";", na, col_names, quote, escape, eol)


def format_tsv(x, na="NA", append=False, col_names=True, quote="needed", escape="double", eol="\n"):
    return format_delim(x, "\t", na, col_names, quote, escape, eol)


def _comma_decimals(x):
    from readr.read import Table

    columns = []
    for column in x.columns:
        converted = []
        for value in column:
            if isinstance(value, float):
                converted.append(format_double(value).replace(".", ","))
            else:
                converted.append(value)
        columns.append(converted)
    return Table(list(x.names), columns, x.nrow)


def output_column(x, name=None):
    """Values as they will be written. Datetimes become UTC ISO-8601 strings."""
    if isinstance(x, datetime):
        return _cell(x, "NA")
    if isinstance(x, (list, tuple)):
        return [_cell(value, "NA") if isinstance(value, datetime) else value for value in x]
    return x


def write_file(x, file, append=False):
    """Write a string or bytes exactly."""
    mode = "ab" if append else "wb"
    data = x if isinstance(x, (bytes, bytearray)) else str(x).encode("utf-8")
    with open(file, mode) as handle:
        handle.write(data)
    return x


def write_lines(x, file, sep="\n", na="NA", append=False):
    """Write one record per line."""
    lines = []
    for value in x:
        if value is None:
            lines.append(na)
        elif isinstance(value, (bytes, bytearray)):
            lines.append(value.decode("utf-8", errors="replace"))
        elif isinstance(value, float):
            lines.append(format_double(value))
        elif isinstance(value, bool):
            lines.append("TRUE" if value else "FALSE")
        else:
            lines.append(str(value))
    payload = sep.join(lines)
    if lines:
        payload += sep
    if append and Path(file).exists():
        with open(file, "a", encoding="utf-8") as handle:
            handle.write(payload)
    else:
        Path(file).write_text(payload, encoding="utf-8")
    return x
