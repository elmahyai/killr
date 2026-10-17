"""xdisplay from xtable 1.8-8."""

from __future__ import annotations

from xtable.table_utils import as_data_frame_columns, is_numeric_vector, r_length_dim
from xtable.xdigits import xdigits


def xdisplay(x: object, pad: bool = True) -> list[str]:
    def type_for(column: list[object]) -> str:
        if is_numeric_vector(column):
            return "d" if xdigits(column, pad=False)[0] == 0 else "f"
        return "s"

    is_2d = r_length_dim(x) == 2
    columns = as_data_frame_columns(x)
    if is_2d:
        disp = [type_for(col) for col in columns]
    else:
        disp = [type_for(columns[0])]
    if is_2d and pad:
        return ["s", *disp]
    return disp
