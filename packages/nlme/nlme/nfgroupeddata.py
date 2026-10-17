"""One-level grouped-data constructor (nlme ``nfGroupedData``)."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from nlme.groupeddata import DataFrame, groupedData


def nfGroupedData(
    form: str,
    data: DataFrame | Mapping[str, Any],
    order_groups: bool = True,
    FUN: Callable | None = None,
    outer: str | None = None,
    inner: str | None = None,
    labels: Mapping[str, str] | None = None,
    units: Mapping[str, str] | None = None,
) -> DataFrame:
    """Construct an ``nfGroupedData`` object from a one-level formula.

    This is the one-level constructor used by R's ``groupedData``.  Validation
    and factor ordering are delegated to the translated ``groupedData`` helper.
    """
    result = groupedData(
        form,
        data=data,
        order_groups=order_groups,
        FUN=FUN,
        outer=outer,
        inner=inner,
        labels=labels,
        units=units,
    )
    if "nfGroupedData" not in result.classes:
        raise ValueError("form must specify exactly one grouping level")
    return result


__all__ = ["nfGroupedData"]
