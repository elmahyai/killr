"""xalign from xtable 1.8-8."""

from __future__ import annotations

from xtable.table_utils import as_data_frame_columns, is_numeric_vector, r_length_dim


def xalign(x: object, pad: bool = True) -> list[str]:
    def lr(column: list[object]) -> str:
        return "r" if is_numeric_vector(column) else "l"

    is_2d = r_length_dim(x) == 2
    columns = as_data_frame_columns(x)
    if is_2d:
        alignment = [lr(col) for col in columns]
    else:
        alignment = [lr(columns[0])]
    if is_2d and pad:
        return ["l", *alignment]
    return alignment
