"""xdigits from xtable 1.8-8."""

from __future__ import annotations

import math

from xtable.table_utils import (
    as_data_frame_columns,
    is_numeric_vector,
    r_length_dim,
    r_nchar,
    r_zapsmall,
)

_DEFAULT_ZAP = 7


def xdigits(x: object, pad: bool = True, zap: int | float | None = None) -> list[int]:
    if zap is None:
        zap = _DEFAULT_ZAP
    zap = int(zap)

    def dig(column: list[object]) -> int:
        if is_numeric_vector(column):
            nums = [float(v) for v in column if v is not None and not _is_na(v)]
            frac = [abs(v - math.floor(v)) for v in nums]
            frac = r_zapsmall(frac, zap)
            if any(v > 0 for v in frac):
                return max(r_nchar(v) - 2 for v in frac)
            return 0
        return 0

    is_2d = r_length_dim(x) == 2
    columns = as_data_frame_columns(x)
    if is_2d:
        decimals = [dig(col) for col in columns]
    else:
        decimals = [dig(columns[0])]
    if is_2d and pad:
        return [0, *decimals]
    return decimals


def _is_na(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    return False
