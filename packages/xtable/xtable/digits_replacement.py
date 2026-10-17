"""digits<- from xtable 1.8-8."""

from __future__ import annotations

from xtable.caption_replacement import Xtable


def digits_replacement(x: object, value: object) -> Xtable:
    if not isinstance(x, Xtable):
        raise ValueError(
            f"no applicable method for 'digits<-' applied to an object of class "
            f'"{type(x).__name__}"'
        )
    ncol = x.ncol
    if isinstance(value, list) and value and isinstance(value[0], list):
        matrix = value
        if len(matrix[0]) != ncol + 1 or len(matrix) != x.nrow:
            raise ValueError(
                "if argument 'digits' is a matrix, it must have columns equal "
                f"to {ncol + 1} ( ncol(x) + 1 ) and rows equal to {x.nrow} "
                f"( nrow( x )"
            )
        x.attrs["digits"] = [list(row) for row in matrix]
    else:
        if isinstance(value, (list, tuple)):
            vec = list(value)
        else:
            vec = [value]
        if len(vec) == 1:
            vec = vec * (ncol + 1)
        elif len(vec) > 1 and len(vec) != ncol + 1:
            raise ValueError(
                "if argument 'digits' is a vector of length more than one, "
                f"it must have length equal to {ncol + 1} ( ncol(x) + 1 )"
            )
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vec):
            raise ValueError('"digits" must be numeric')
        x.attrs["digits"] = vec
    return x
