"""Spatial correlation factory (nlme corSpatial)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from nlme.corlin import CorLin, corLin
from nlme.corratio import CorRatio, corRatio
from nlme.corspher import CorSpher, corSpher
from nlme.corexp import CorExp, corExp
from nlme.corgaus import CorGaus, corGaus

_TYPES = ("spherical", "exponential", "gaussian", "linear", "rational")


def _match_type(type_: str) -> str:
    if type_ in _TYPES:
        return type_
    matches = [name for name in _TYPES if name.startswith(type_)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"'{type_}' is ambiguous")
    raise ValueError(f"'{type_}' is not a valid type")


def corSpatial(
    value: float | Sequence[float] | np.ndarray = (),
    form: str = "~ 1",
    nugget: bool = False,
    type: str = "spherical",
    metric: str = "euclidean",
    fixed: bool = False,
) -> CorSpher | CorExp | CorGaus | CorLin | CorRatio:
    """Construct a spatial correlation object of the requested ``type``."""
    kind = _match_type(type)
    if kind == "spherical":
        return corSpher(value, form=form, nugget=nugget, metric=metric, fixed=fixed)
    if kind == "exponential":
        return corExp(value, form=form, nugget=nugget, metric=metric, fixed=fixed)
    if kind == "gaussian":
        return corGaus(value, form=form, nugget=nugget, metric=metric, fixed=fixed)
    if kind == "linear":
        return corLin(value, form=form, nugget=nugget, metric=metric, fixed=fixed)
    return corRatio(value, form=form, nugget=nugget, metric=metric, fixed=fixed)
