"""Flatten nested data frames and bind pages that do not share every column."""

from __future__ import annotations

from jsonlite._values import NA, DataFrame


def flatten(x: DataFrame, recursive: bool = True) -> DataFrame:
    """Lift nested data-frame columns, prefixing their names with the parent column."""

    if not isinstance(x, DataFrame):
        raise TypeError("flatten expects a data frame")
    columns: dict[str, list | DataFrame] = {}
    for name, values in x.columns.items():
        if isinstance(values, DataFrame):
            nested = flatten(values) if recursive else values
            for child, child_values in nested.columns.items():
                columns[f"{name}.{child}"] = child_values
        else:
            columns[name] = values
    return DataFrame(columns)  # type: ignore[arg-type]


def rbind_pages(pages: list) -> DataFrame:
    """Bind data frames, filling a column missing from a page with NA."""

    frames = [page for page in pages if page is not None]
    if any(not isinstance(page, DataFrame) for page in frames):
        raise TypeError("pages must be data frames")
    names: list[str] = []
    for frame in frames:
        for name in frame.columns:
            if name not in names and not isinstance(frame.columns[name], DataFrame):
                names.append(name)
            elif name not in names:
                names.append(name)
    columns: dict[str, list] = {name: [] for name in names}
    for frame in frames:
        for name in names:
            values = frame.columns.get(name)
            if values is None:
                columns[name].extend([NA] * len(frame))
            elif isinstance(values, DataFrame):
                raise TypeError("nested pages are left for a later pass")
            else:
                columns[name].extend(values)
    return DataFrame(columns)
