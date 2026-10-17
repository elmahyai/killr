"""Row-bind heterogeneous tabular objects (gtools 3.9.5 ``smartbind``)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import polars as pl


def _as_frame(value: Any) -> pl.DataFrame:
    if isinstance(value, pl.DataFrame):
        return value
    if isinstance(value, pl.Series):
        return value.to_frame()
    if isinstance(value, Mapping):
        columns = {}
        for key, column in value.items():
            if isinstance(column, Sequence) and not isinstance(
                column, (str, bytes, bytearray)
            ):
                columns[str(key)] = column
            else:
                columns[str(key)] = [column]
        return pl.DataFrame(columns)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return pl.DataFrame({str(i + 1): [v] for i, v in enumerate(value)})
    raise TypeError("smartbind inputs must be Polars DataFrames, Series, mappings, or sequences")


def _fill_value(value: Any, dtype: pl.DataType) -> Any:
    if value is None:
        return None
    if dtype == pl.String:
        return str(value)
    if dtype == pl.Boolean:
        return bool(value)
    return value


def smartbind(
    *args: Any,
    list: Mapping[str, Any] | None = None,
    fill: Any = None,
    sep: str = ":",
    verbose: bool = False,
) -> pl.DataFrame:
    """Bind rows while preserving columns absent from individual inputs.

    ``list`` supplies named inputs and positional inputs override duplicate
    names, matching R's ``modifyList(list, data)`` behavior.  ``sep`` is
    accepted for API compatibility; Polars has no row-name column.
    """
    del sep
    items: list[tuple[str, Any]] = []
    if list is not None:
        items.extend((str(name), value) for name, value in list.items())
    items.extend((str(index + 1), value) for index, value in enumerate(args))
    frames: list[pl.DataFrame] = []
    for name, value in items:
        frame = _as_frame(value)
        if frame.height and frame.width:
            if verbose:
                print(frame.head())
            frames.append(frame)
    if not frames:
        return pl.DataFrame()

    result = pl.concat(frames, how="diagonal_relaxed")
    if fill is not None:
        replacements = {
            column: pl.lit(_fill_value(fill, dtype), dtype=dtype)
            for column, dtype in zip(result.columns, result.dtypes)
        }
        result = result.with_columns(
            pl.when(pl.col(column).is_null())
            .then(replacement)
            .otherwise(pl.col(column))
            .alias(column)
            for column, replacement in replacements.items()
        )
    return result


__all__ = ["smartbind"]
