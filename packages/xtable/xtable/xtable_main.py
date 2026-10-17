"""xtable from xtable 1.8-8 (``xtable`` generic and core methods)."""

from __future__ import annotations

from xtable.align_replacement import align_replacement
from xtable.caption_replacement import Xtable, caption_replacement
from xtable.digits_replacement import digits_replacement
from xtable.display_replacement import display_replacement
from xtable.label_replacement import label_replacement


class Factor:
    """Stand-in for an R factor column."""

    __slots__ = ("values", "levels")

    def __init__(self, values: list[object], *, levels: list[object] | None = None) -> None:
        self.values = list(values)
        if levels is None:
            seen: dict[object, None] = {}
            ordered: list[object] = []
            for value in self.values:
                if value not in seen:
                    seen[value] = None
                    ordered.append(value)
            self.levels = ordered
        else:
            self.levels = list(levels)


class RDataFrame:
    """Column-oriented data.frame input for ``xtable``."""

    __slots__ = ("columns", "row_names")

    def __init__(
        self,
        columns: dict[str, list[object]],
        *,
        row_names: list[object] | None = None,
    ) -> None:
        self.columns = columns
        self.row_names = row_names


def _is_matrix(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    if not isinstance(value[0], list):
        return False
    width = len(value[0])
    return all(isinstance(row, list) and len(row) == width for row in value)


def _logical_to_character(values: list[object]) -> list[str]:
    out: list[str] = []
    for item in values:
        if item is True:
            out.append("TRUE")
        elif item is False:
            out.append("FALSE")
        else:
            out.append(str(item))
    return out


def _column_values(column: object) -> list[object]:
    if isinstance(column, Factor):
        return list(column.values)
    if isinstance(column, list):
        return list(column)
    return [column]


def _is_logical_column(column: object) -> bool:
    values = _column_values(column)
    return bool(values) and all(isinstance(v, bool) for v in values)


def _rows_from_columns(columns: dict[str, list[object]]) -> list[list[object]]:
    if not columns:
        return []
    names = list(columns.keys())
    n = len(columns[names[0]])
    rows: list[list[object]] = []
    for i in range(n):
        rows.append([columns[name][i] for name in names])
    return rows


def _data_frame_from_matrix(
    matrix: list[list[object]], *, check_names: bool = False
) -> RDataFrame:
    if not matrix:
        return RDataFrame({})
    ncol = len(matrix[0])
    columns: dict[str, list[object]] = {}
    for j in range(ncol):
        name = str(j + 1)
        columns[name] = [row[j] for row in matrix]
    return RDataFrame(columns)


def xtable_data_frame(
    x: RDataFrame,
    *,
    caption=None,
    label=None,
    align=None,
    digits=None,
    display=None,
    auto: bool = False,
) -> Xtable:
    columns = {name: _column_values(col) for name, col in x.columns.items()}
    for name, values in list(columns.items()):
        if _is_logical_column(x.columns[name]):
            columns[name] = _logical_to_character(values)

    col_names = list(columns.keys())
    data = _rows_from_columns(columns)
    xt = Xtable(
        data,
        classes=("xtable", "data.frame"),
        col_names=col_names,
        row_names=x.row_names,
    )
    if caption is not None:
        caption_replacement(xt, caption)
    if label is not None:
        label_replacement(xt, label)

    characters = [
        all(isinstance(v, str) for v in columns[name]) for name in col_names
    ]
    factors = [isinstance(x.columns[name], Factor) for name in col_names]
    ints = [
        all(isinstance(v, int) and not isinstance(v, bool) for v in columns[name])
        for name in col_names
    ]

    align_val = align
    if align_val is None:
        align_val = ["r"] + ["l" if (characters[i] or factors[i]) else "r" for i in range(len(col_names))]
    align_replacement(xt, align_val)

    digits_val = digits
    if digits_val is None:
        digits_val = [0] + [2] * len(col_names)
    digits_replacement(xt, digits_val)

    display_val = display
    if display_val is None:
        disp = ["f"] * len(col_names)
        for i, is_int in enumerate(ints):
            if is_int:
                disp[i] = "d"
        for i, is_chr in enumerate(characters):
            if is_chr or factors[i]:
                disp[i] = "s"
        display_val = ["s"] + disp
    display_replacement(xt, display_val)
    return xt


def xtable_matrix(
    x: list[list[object]],
    *,
    caption=None,
    label=None,
    align=None,
    digits=None,
    display=None,
    auto: bool = False,
) -> Xtable:
    frame = _data_frame_from_matrix(x, check_names=False)
    return xtable_data_frame(
        frame,
        caption=caption,
        label=label,
        align=align,
        digits=digits,
        display=display,
        auto=auto,
    )


def xtable(
    x: object,
    caption=None,
    label=None,
    align=None,
    digits=None,
    display=None,
    auto: bool = False,
    **_kwargs: object,
) -> Xtable:
    if isinstance(x, RDataFrame):
        return xtable_data_frame(
            x,
            caption=caption,
            label=label,
            align=align,
            digits=digits,
            display=display,
            auto=auto,
        )
    if _is_matrix(x):
        return xtable_matrix(
            x,
            caption=caption,
            label=label,
            align=align,
            digits=digits,
            display=display,
            auto=auto,
        )
    if isinstance(x, Xtable):
        return xtable_data_frame(
            RDataFrame(
                {
                    (x.col_names[i] if x.col_names else f"V{i + 1}"): [
                        row[i] for row in x.data
                    ]
                    for i in range(x.ncol)
                }
            ),
            caption=caption,
            label=label,
            align=align,
            digits=digits,
            display=display,
            auto=auto,
        )
    kind = type(x).__name__
    raise ValueError(
        f"no applicable method for 'xtable' applied to an object of class \"{kind}\""
    )
