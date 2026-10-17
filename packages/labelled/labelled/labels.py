"""Label and dictionary helpers for the labelled package.

The R package attaches metadata to vectors and data-frame columns.  Python
uses explicit objects for that metadata, while Polars is used for tables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import polars as pl


@dataclass
class HavenLabelled:
    values: Any
    labels: dict[Any, str] = field(default_factory=dict)
    variable_label: str | None = None
    na_values: Any = None
    na_range: Any = None

    def copy(self) -> "HavenLabelled":
        return HavenLabelled(
            np.array(self.values, copy=True),
            dict(self.labels),
            self.variable_label,
            self.na_values,
            self.na_range,
        )

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, item):
        return self.values[item]


def _is_labelled(x):
    return isinstance(x, HavenLabelled)


def _label(x):
    return x.variable_label if _is_labelled(x) else getattr(x, "variable_label", None)


def _labels(x):
    return dict(x.labels) if _is_labelled(x) else {}


def _set_column(df, name, value):
    if isinstance(df, pl.DataFrame):
        return df.with_columns(pl.Series(name, value))
    out = dict(df)
    out[name] = value
    return out


def _columns(df):
    return df.columns if isinstance(df, pl.DataFrame) else list(df)


def copy_labels(from_, to, strict: bool = True, **kwargs):
    """Copy variable/value labels and user-missing metadata."""
    if isinstance(to, pl.DataFrame):
        if not isinstance(from_, pl.DataFrame):
            raise TypeError("from_ should also be a data frame")
        out = to
        for name in to.columns:
            if name in from_.columns:
                out = _set_column(out, name, copy_labels(from_[name].to_list(),
                                                         to[name].to_list(),
                                                         strict))
        return out
    if isinstance(from_, HavenLabelled):
        if strict and type(from_.values) is not type(np.asarray(to)):
            # R's strict check is numeric versus character; preserve the
            # useful common case without rejecting ordinary NumPy arrays.
            if np.asarray(from_.values).dtype.kind != np.asarray(to).dtype.kind:
                raise TypeError("from_ and to must be of same type")
        if isinstance(to, HavenLabelled):
            out = to.copy()
        else:
            out = HavenLabelled(np.asarray(to, copy=True))
        out.variable_label = from_.variable_label
        if np.asarray(from_.values).dtype.kind == np.asarray(out.values).dtype.kind:
            out.labels = dict(from_.labels)
            out.na_values, out.na_range = from_.na_values, from_.na_range
        return out
    if isinstance(to, HavenLabelled):
        out = to.copy()
        out.variable_label = _label(from_)
        return out
    return to


def copy_labels_from(to, from_, strict: bool = True, **kwargs):
    return copy_labels(from_, to, strict=strict, **kwargs)


def _col(dictionary, spec):
    if isinstance(spec, int):
        return dictionary.columns[spec - 1] if isinstance(dictionary, pl.DataFrame) else list(dictionary)[spec - 1]
    return spec


def _rows(dictionary):
    return dictionary.to_dicts() if isinstance(dictionary, pl.DataFrame) else dictionary


def dictionary_to_variable_labels(dictionary, names_from=1, labels_from=2):
    n, l = _col(dictionary, names_from), _col(dictionary, labels_from)
    result = {}
    for row in _rows(dictionary):
        if row[n] is not None:
            result[row[n]] = row[l]
    return result


def dictionary_to_value_labels(
    dictionary, names_from=1, values_from=2, labels_from=3,
    delim_entries=None, delim_value_label=None, data=None,
):
    n, v, l = (_col(dictionary, z) for z in (names_from, values_from, labels_from))
    result: dict[Any, dict[Any, Any]] = {}
    for row in _rows(dictionary):
        name, value = row[n], row[v]
        if name is None or value is None:
            continue
        entries = str(value).split(delim_entries) if delim_entries else [value]
        for entry in entries:
            if delim_value_label is not None:
                parts = str(entry).split(delim_value_label, 1)
                val, lab = parts[0], parts[1] if len(parts) > 1 else ""
            else:
                val, lab = entry, row[l]
            result.setdefault(name, {})[val] = lab
    if data is not None:
        names = _columns(data)
        for name, labels in result.items():
            if name in names:
                dtype = data[name].dtype if isinstance(data, pl.DataFrame) else np.asarray(data[name]).dtype
                converted = {}
                for value, lab in labels.items():
                    try:
                        value = np.asarray([value]).astype(dtype)[0].item()
                    except (TypeError, ValueError):
                        pass
                    converted[value] = lab
                result[name] = converted
    return result


def drop_unused_value_labels(x):
    if isinstance(x, HavenLabelled):
        present = set(np.asarray(x.values).tolist())
        out = x.copy()
        out.labels = {k: v for k, v in x.labels.items() if k in present}
        return out
    if isinstance(x, pl.DataFrame):
        return x
    return x


def is_prefixed(x):
    if not isinstance(x, (list, tuple, np.ndarray, pl.Series)):
        raise TypeError("is_prefixed should be used only with a factor")
    codes = []
    for value in x:
        match = re.match(r"^\[(.+)\]\s(.+)$", str(value))
        if not match:
            return False
        codes.append(match.group(1))
    return len(codes) == len(set(codes))


def convert_list_columns_to_character(x, sep_value_labels="[]", sep_other="; "):
    if not isinstance(x, pl.DataFrame):
        return x
    out = x
    for name in x.columns:
        if x[name].dtype == pl.List:
            out = out.with_columns(
                pl.col(name).map_elements(
                    lambda v: sep_other.join("" if z is None else str(z) for z in (v or [])),
                    return_dtype=pl.String,
                ).alias(name)
            )
    return out


def _search(value, pattern, ignore_case):
    flags = re.IGNORECASE if ignore_case else 0
    try:
        return re.search(pattern, str(value), flags) is not None
    except re.error:
        return pattern.lower() in str(value).lower() if ignore_case else pattern in str(value)


def look_for(data, *keywords, labels=True, values=True, ignore_case=True,
             ignore_case_=None, details="basic", **kwargs):
    if not isinstance(data, pl.DataFrame):
        raise TypeError("data must be a Polars DataFrame")
    if ignore_case_ is not None:
        ignore_case = ignore_case_
    rows = []
    for pos, name in enumerate(data.columns, 1):
        hit = not keywords
        label = data[name].meta if False else None
        if keywords:
            hit = _search(name, "|".join(map(str, keywords)), ignore_case)
        if hit:
            row = {"pos": pos, "variable": name, "label": label}
            if details != "none":
                vals = data[name].to_list()
                row.update(col_type=str(data[name].dtype), missing=sum(v is None for v in vals),
                           levels=None, value_labels=None)
            if details == "full":
                vals = [v for v in data[name].to_list() if v is not None]
                row.update(class_=[str(data[name].dtype)], type=str(data[name].dtype),
                           na_values=None, na_range=None, n_na=row["missing"],
                           unique_values=len(set(map(str, vals))),
                           range=[min(vals), max(vals)] if vals and all(isinstance(v, (int, float)) for v in vals) else None)
            rows.append(row)
    return pl.DataFrame(rows) if rows else pl.DataFrame()


def look_for_and_select(data, *keywords, **kwargs):
    result = look_for(data, *keywords, details="none", **kwargs)
    return data.select(result["variable"].to_list()) if result.height else data.select([])


def lookfor_to_long_format(x, sep_value_labels="[]"):
    if not isinstance(x, pl.DataFrame) or not {"levels", "value_labels"} <= set(x.columns):
        return x
    return x.explode(["levels", "value_labels"])


def to_gt(x, *args, **kwargs):
    raise ImportError("to_gt is blocked on the unregistered gt package")
