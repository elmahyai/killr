"""Read and write SPSS, Stata, and SAS files."""

from __future__ import annotations

import os
import re
import unicodedata
import warnings
from pathlib import Path

import havenio
from tibble import new_tibble

from haven.labelled import Vector
from haven.tagged import is_na_double, na_real

_SPSS_RESERVED = {
    "ALL", "AND", "BY", "EQ", "GE", "GT", "LE", "LT", "NE", "NOT", "OR", "TO", "WITH",
}


def read_dta(file, encoding=None, col_select=None, skip=0, n_max=float("inf"), name_repair="unique"):
    """Read a Stata DTA file."""
    return _read("dta", file, encoding=encoding, col_select=col_select, skip=skip, n_max=n_max, name_repair=name_repair)


def read_stata(file, encoding=None, col_select=None, skip=0, n_max=float("inf"), name_repair="unique"):
    """Read a Stata DTA file. This is read_dta."""
    return read_dta(file, encoding=encoding, col_select=col_select, skip=skip, n_max=n_max, name_repair=name_repair)


def read_sav(file, encoding=None, user_na=False, col_select=None, skip=0, n_max=float("inf"), name_repair="unique"):
    """Read an SPSS .sav or .zsav file."""
    return _read(
        "sav", file, encoding=encoding, user_na=user_na, col_select=col_select,
        skip=skip, n_max=n_max, name_repair=name_repair,
    )


def read_por(file, user_na=False, col_select=None, skip=0, n_max=float("inf"), name_repair="unique"):
    """Read an SPSS .por file."""
    return _read(
        "por", file, user_na=user_na, col_select=col_select, skip=skip,
        n_max=n_max, name_repair=name_repair,
    )


def read_spss(file, user_na=False, col_select=None, skip=0, n_max=float("inf"), name_repair="unique"):
    """Read an SPSS file, choosing the reader from the extension."""
    ext = Path(str(file)).suffix.lower().lstrip(".")
    if ext in ("sav", "zsav"):
        return read_sav(file, user_na=user_na, col_select=col_select, skip=skip, n_max=n_max, name_repair=name_repair)
    if ext == "por":
        return read_por(file, user_na=user_na, col_select=col_select, skip=skip, n_max=n_max, name_repair=name_repair)
    raise ValueError(f"Unknown extension .{ext}.")


def read_sas(data_file, catalog_file=None, encoding=None, catalog_encoding=None, col_select=None, skip=0, n_max=float("inf"), cols_only=None, name_repair="unique"):
    """Read a SAS sas7bdat file, with an optional sas7bcat catalog."""
    if cols_only is not None:
        warnings.warn(
            "The `cols_only` argument of `read_sas()` is deprecated as of haven 2.2.0. Please use the `col_select` argument instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if isinstance(cols_only, str):
            cols_only = [cols_only]
        col_select = list(cols_only)
    if catalog_encoding is None:
        catalog_encoding = encoding
    return _read(
        "sas", data_file, encoding=encoding, col_select=col_select, skip=skip,
        n_max=n_max, name_repair=name_repair, catalog=catalog_file,
        catalog_encoding=catalog_encoding,
    )


def read_xpt(file, col_select=None, skip=0, n_max=float("inf"), name_repair="unique"):
    """Read a SAS transport file."""
    return _read("xpt", file, col_select=col_select, skip=skip, n_max=n_max, name_repair=name_repair)


def write_dta(data, path, version=14, label=None, strl_threshold=2045, adjust_tz=True):
    """Write a Stata DTA file. Returns data."""
    _validate_dta(data, version)
    if label is None:
        label = getattr(data, "label", None)
    _validate_dta_label(label)
    if strl_threshold < 0 or strl_threshold > 2045:
        strl_threshold = 2045
    payload = _prepare(data, adjust_tz=adjust_tz)
    havenio.write_table(
        "dta", os.path.abspath(path), payload,
        label=label, version=_stata_format(version), strl_threshold=int(strl_threshold),
    )
    return data


def write_sav(data, path, compress="byte", adjust_tz=True):
    """Write an SPSS .sav file. Returns data."""
    if compress is True:
        compress = "zsav"
    elif compress is False:
        compress = "none"
    elif compress not in ("byte", "none", "zsav"):
        raise ValueError('compress must be "byte", "none", or "zsav"')
    _validate_sav(data)
    payload = _prepare(data, adjust_tz=adjust_tz)
    havenio.write_table("sav", os.path.abspath(path), payload, compress=compress)
    return data


def write_sas(data, path):
    """Write a sas7bdat file. Deprecated in favor of write_xpt."""
    warnings.warn(
        "`write_sas()` was deprecated in haven 2.5.2. Please use `write_xpt()` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    payload = _prepare(data, adjust_tz=True)
    havenio.write_table("sas", os.path.abspath(path), payload)
    return data


def write_xpt(data, path, version=8, name=None, label=None, adjust_tz=True):
    """Write a SAS transport file. Returns data."""
    if version not in (5, 8):
        raise ValueError(f"SAS transport file version {version} is not currently supported.")
    if name is None:
        name = Path(path).stem
    if version == 5 and len(name) > 8:
        raise ValueError("`name` must be 8 characters or fewer.")
    if version == 8 and len(name) > 32:
        raise ValueError("`name` must be 32 characters or fewer.")
    if label is None:
        label = getattr(data, "label", None)
    if label is not None and len(label) > 40:
        raise ValueError("`label` must be 40 characters or fewer.")
    payload = _prepare(data, adjust_tz=adjust_tz)
    havenio.write_table("xpt", os.path.abspath(path), payload, version=int(version), name=name, label=label)
    return data


def _read(kind, file, encoding=None, user_na=False, col_select=None, skip=0, n_max=float("inf"), name_repair="unique", catalog=None, catalog_encoding=None):
    path, data = _source(file)
    catalog_path, catalog_data = _source(catalog) if catalog is not None else (None, None)
    limit = _n_max(n_max)
    skip_names = []
    if col_select is not None:
        preview = havenio.read_table(
            kind, path=path, data=data, encoding=encoding or "", user_na=user_na,
            n_max=0, rows_skip=0, catalog_path=catalog_path, catalog_data=catalog_data,
            catalog_encoding=catalog_encoding or "",
        )
        names = [column["name"] for column in preview["columns"]]
        skip_names = _skip_names(names, col_select)
    raw = havenio.read_table(
        kind, path=path, data=data, encoding=encoding or "", user_na=user_na,
        cols_skip=skip_names, n_max=limit, rows_skip=int(skip),
        catalog_path=catalog_path, catalog_data=catalog_data,
        catalog_encoding=catalog_encoding or "",
    )
    return _frame(raw, name_repair)


def _source(file):
    if file is None:
        return None, None
    if isinstance(file, (bytes, bytearray)):
        return None, bytes(file)
    return os.fspath(file), None


def _n_max(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"`n_max` must be numeric, not {type(value).__name__}.")
    if value != value or value == float("inf") or value < 0:
        return -1
    return int(value)


def _skip_names(names, col_select):
    if isinstance(col_select, (str, int)):
        col_select = [col_select]
    chosen = []
    for item in col_select:
        if isinstance(item, int):
            if item < 1 or item > len(names):
                raise ValueError("Can't find any columns matching `col_select` in data.")
            chosen.append(names[item - 1])
        else:
            if item not in names:
                raise ValueError("Can't find any columns matching `col_select` in data.")
            chosen.append(item)
    if not chosen:
        raise ValueError("Can't find any columns matching `col_select` in data.")
    return [name for name in names if name not in chosen]


def _frame(raw, name_repair):
    names = [column["name"] for column in raw["columns"]]
    if name_repair == "unique":
        names = _unique_names(names)
    elif name_repair == "check_unique":
        if any(name == "" for name in names) or len(set(names)) != len(names):
            raise ValueError("column names must be unique and non-empty")
    elif name_repair != "minimal":
        raise ValueError("name_repair must be check_unique, unique, or minimal")
    columns = [_column(spec) for spec in raw["columns"]]
    frame = new_tibble(columns, nrow=int(raw["nrows"]), names=names)
    frame.label = raw.get("label")
    frame.notes = list(raw.get("notes") or [])
    return frame


def _unique_names(names):
    seen = {}
    out = []
    for name in names:
        if name not in seen:
            seen[name] = 0
            out.append(name)
            continue
        seen[name] += 1
        candidate = f"{name}...{seen[name]}"
        while candidate in seen:
            seen[name] += 1
            candidate = f"{name}...{seen[name]}"
        seen[candidate] = 0
        out.append(candidate)
    return out


def _column(spec) -> Vector:
    storage = spec["storage"]
    values = list(spec["values"])
    if storage == "double":
        values = [float(item) for item in values]
    column = Vector(values, "string" if storage == "string" else "double")
    column.label = spec.get("label")
    column.class_ = list(spec.get("class") or [])
    column.units = spec.get("units")
    column.tzone = spec.get("tzone")
    column.display_width = spec.get("display_width")
    fmt = spec.get("format")
    if "format.stata" in spec:
        column.format_stata = spec["format.stata"]
    if fmt:
        if "Date" in column.class_ or "POSIXct" in column.class_ or "hms" in column.class_:
            pass
        # The format attribute name depends on the file. The reader stores the text only.
    names = spec.get("label_names") or []
    label_values = spec.get("label_values") or []
    column.labels = list(zip(label_values, names))
    if spec.get("na_values") is not None:
        column.na_values = list(spec["na_values"])
    if spec.get("na_range") is not None:
        column.na_range = list(spec["na_range"])
    # The Rust reader reports the format string but not which attribute name it uses.
    # Class tells us the kind; the attribute is filled by the caller via spec["format_attr"] when present.
    attr = spec.get("format_attr")
    if attr == "format.stata":
        column.format_stata = fmt
    elif attr == "format.spss":
        column.format_spss = fmt
    elif attr == "format.sas":
        column.format_sas = fmt
    return column


def _prepare(data, adjust_tz):
    columns = []
    for name, column in zip(data.names, data.columns):
        if not isinstance(column, Vector):
            column = _plain(column)
        if adjust_tz and "POSIXct" in column.class_:
            column = _force_utc(column)
        columns.append(_payload(name, column))
    return columns


def _plain(values) -> Vector:
    values = list(values)
    if values and isinstance(values[0], str):
        return Vector(values, "string")
    if values and isinstance(values[0], bool):
        out = Vector([i32_missing if item is None else int(item) for item in values], "logical")
        return out
    return Vector([na_real() if item is None else float(item) for item in values], "double")


i32_missing = -2147483648


def _payload(name, column: Vector) -> dict:
    storage = column.storage
    if storage == "string":
        values = column.values
        kind = "string"
    elif storage == "logical":
        values = [i32_missing if item is None else int(item) for item in column.values]
        kind = "logical"
    elif storage == "integer":
        values = [i32_missing if item is None else int(item) for item in column.values]
        kind = "integer"
    else:
        values = [na_real() if item is None or (isinstance(item, float) and item != item and not _keep_nan(item)) else float(item) for item in column.values]
        kind = "double"
    payload = {
        "name": name,
        "storage": kind,
        "values": values,
        "label": column.label,
        "class": column.class_,
        "format_stata": column.format_stata,
        "format_spss": column.format_spss,
        "format_sas": column.format_sas,
        "display_width": column.display_width or 0,
        "width": column.width or 0,
        "levels": column.levels or [],
        "ordered": column.ordered,
        "labelled": is_labelled_class(column),
        "spss": "haven_labelled_spss" in column.class_,
        "label_names": [name for _value, name in column.labels],
    }
    if column.labels and kind == "string":
        payload["labels_string"] = [value for value, _name in column.labels]
    elif column.labels and kind == "integer":
        payload["labels_int"] = [int(value) for value, _name in column.labels]
    elif column.labels:
        payload["labels_double"] = [float(value) for value, _name in column.labels]
    if column.na_values and kind == "string":
        payload["na_values_string"] = list(column.na_values)
    elif column.na_values and kind == "integer":
        payload["na_values_int"] = [int(value) for value in column.na_values]
    elif column.na_values:
        payload["na_values_double"] = [float(value) for value in column.na_values]
    if column.na_range and kind == "string":
        payload["na_range_string"] = [str(value) for value in column.na_range]
    elif column.na_range:
        payload["na_range_double"] = [float(value) for value in column.na_range]
    return payload


def is_labelled_class(column: Vector) -> bool:
    return any(name in column.class_ for name in ("haven_labelled", "haven_labelled_spss"))


def _keep_nan(item) -> bool:
    return isinstance(item, float) and item != item


def _force_utc(column: Vector) -> Vector:
    if column.tzone in (None, "UTC"):
        return column
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    out = column.copy()
    zone = ZoneInfo(column.tzone)
    converted = []
    for value in out.values:
        if is_na_double(value):
            converted.append(value)
            continue
        wall = datetime.fromtimestamp(value, zone).replace(tzinfo=None)
        converted.append(wall.replace(tzinfo=timezone.utc).timestamp())
    out.values = converted
    out.tzone = "UTC"
    return out


def _stata_format(version: int) -> int:
    version = int(version)
    table = {15: 119, 14: 118, 13: 117, 12: 115, 11: 114, 10: 114, 9: 113, 8: 113}
    if version not in table:
        raise ValueError(f"Stata version {version} is not currently supported.")
    return table[version]


def _validate_dta_label(label):
    if label is not None and len(label) > 80:
        raise ValueError("`label` must be 80 characters or fewer.")


def _validate_dta(data, version):
    bad = []
    for name in data.names:
        too_long = len(name) > 32
        bad_shape = version < 14 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]+", name) is None
        if too_long or bad_shape:
            bad.append(name)
    if bad:
        raise ValueError("Variables in `data` must have valid Stata variable names. Problems: " + ", ".join(bad))
    for name, column in zip(data.names, data.columns):
        if not isinstance(column, Vector) or column.storage != "double" or not column.labels:
            continue
        if not is_labelled_class(column):
            continue
        if not _integerish([value for value, _label in column.labels]):
            raise ValueError("Stata only supports labelling with integer variables. Problems: " + name)


def _integerish(values) -> bool:
    for value in values:
        if is_na_double(value):
            continue
        if not isinstance(value, (int, float)) or value != int(value):
            return False
    return True


def _validate_sav(data):
    bad = []
    for name in data.names:
        if not _spss_name(name) or name.upper() in _SPSS_RESERVED or len(name.encode("utf-8")) > 64:
            bad.append(name)
    if bad:
        raise ValueError("Variables in `data` must have valid SPSS variable names. Problems: " + ", ".join(bad))
    lowered = [name.lower() for name in data.names]
    dupes = [name for name, count in ((name, lowered.count(name.lower())) for name in data.names) if count > 1]
    if dupes:
        raise ValueError("SPSS does not allow duplicate variable names. Problems: " + ", ".join(dupes))
    long_levels = []
    for name, column in zip(data.names, data.columns):
        if isinstance(column, Vector) and column.levels and any(len(level) > 120 for level in column.levels):
            long_levels.append(name)
    if long_levels:
        raise ValueError("SPSS only supports levels with <= 120 characters. Problems: " + ", ".join(long_levels))


def _spss_name(name: str) -> bool:
    if not name:
        return False
    first = name[0]
    if first != "@" and not unicodedata.category(first).startswith("L"):
        return False
    if len(name) == 1:
        return True
    for char in name[1:-1]:
        category = unicodedata.category(char)
        if category.startswith("L") or category.startswith("N") or category == "Sc" or char in "._$#@":
            continue
        return False
    last = name[-1]
    category = unicodedata.category(last)
    return category.startswith("L") or category.startswith("N") or category == "Sc" or last in "_$#@"
