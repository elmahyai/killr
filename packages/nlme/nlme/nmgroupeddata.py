"""Multiple-level grouped-data constructor (nlme ``nmGroupedData``)."""

from __future__ import annotations

from typing import Any, Mapping

from nlme.groupeddata import DataFrame, groupedData


def nmGroupedData(
    form: str,
    data: DataFrame | Mapping[str, Any],
    outer: str | None = None,
    inner: str | None = None,
    labels: Mapping[str, str] | None = None,
    units: Mapping[str, str] | None = None,
) -> DataFrame:
    """Construct an ``nmGroupedData`` object from a multi-level formula."""
    result = groupedData(
        form,
        data=data,
        outer=outer,
        inner=inner,
        labels=labels,
        units=units,
    )
    if "nmGroupedData" not in result.classes:
        raise ValueError("form must specify multiple grouping levels")
    return result


__all__ = ["nmGroupedData"]
