"""Drop labels, formats, widths, empty strings, and special missing values."""

from __future__ import annotations

from haven.labelled import Vector, is_labelled, is_missing
from haven.tagged import is_na_double, na_real


def _columns(x):
    if hasattr(x, "columns") and hasattr(x, "names"):
        return list(zip(x.names, x.columns))
    return None


def _replace_frame(x, columns):
    x.columns = [column for _name, column in columns]
    return x


def zap_labels(x, user_na=False):
    """Remove value labels. SPSS user missings become NA unless user_na is true."""
    pairs = _columns(x)
    if pairs is not None:
        x.columns = [zap_labels(column, user_na=user_na) for _name, column in pairs]
        return x
    if not isinstance(x, Vector) or not is_labelled(x):
        return x
    out = x.copy()
    if "haven_labelled_spss" in out.class_ and not user_na:
        missing = is_missing(out)
        fill = None if out.storage == "string" else na_real()
        for index, flag in enumerate(missing):
            if flag:
                out.values[index] = fill
    out.labels = []
    out.na_values = None
    out.na_range = None
    out.class_ = [name for name in out.class_ if name not in ("haven_labelled", "haven_labelled_spss", "vctrs_vctr", "double", "character")]
    return out


def zap_label(x):
    """Remove the variable label."""
    pairs = _columns(x)
    if pairs is not None:
        x.columns = [zap_label(column) for _name, column in pairs]
        return x
    if isinstance(x, Vector):
        out = x.copy()
        out.label = None
        return out
    return x


def zap_missing(x):
    """Turn tagged and user-defined missing values into plain NA."""
    pairs = _columns(x)
    if pairs is not None:
        x.columns = [zap_missing(column) for _name, column in pairs]
        return x
    if not isinstance(x, Vector) or not is_labelled(x):
        return x
    out = x.copy()
    missing = is_missing(out)
    fill = None if out.storage == "string" else na_real()
    for index, flag in enumerate(missing):
        if flag:
            out.values[index] = fill
    if "haven_labelled_spss" in out.class_:
        out.na_values = None
        out.na_range = None
        out.class_ = [name for name in out.class_ if name != "haven_labelled_spss"]
        if "haven_labelled" not in out.class_:
            out.class_.insert(0, "haven_labelled")
    out.labels = [
        (value, name)
        for value, name in out.labels
        if not (is_na_double(value) or value is None)
    ]
    return out


def zap_formats(x):
    """Remove format.spss, format.sas, and format.stata."""
    pairs = _columns(x)
    if pairs is not None:
        x.columns = [zap_formats(column) for _name, column in pairs]
        return x
    if isinstance(x, Vector):
        out = x.copy()
        out.format_spss = None
        out.format_sas = None
        out.format_stata = None
        return out
    return x


def zap_widths(x):
    """Remove display_width."""
    pairs = _columns(x)
    if pairs is not None:
        x.columns = [zap_widths(column) for _name, column in pairs]
        return x
    if isinstance(x, Vector):
        out = x.copy()
        out.display_width = None
        return out
    return x


def zap_empty(x):
    """Replace empty strings with missing values."""
    if isinstance(x, Vector):
        if x.storage != "string":
            raise ValueError("x must be a character vector")
        out = x.copy()
        out.values = [None if item == "" else item for item in out.values]
        return out
    values = list(x)
    if any(item is not None and not isinstance(item, str) for item in values):
        raise ValueError("x must be a character vector")
    return [None if item == "" else item for item in values]
