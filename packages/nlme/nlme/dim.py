"""Dimensions of nlme objects (R generic ``Dim`` and its methods)."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from nlme import corstruct
from nlme.corar1 import CorAR1
from nlme.corarma import CorARMA
from nlme.corcar1 import CorCAR1
from nlme.corcompsymm import CorCompSymm
from nlme.corexp import CorExp
from nlme.corgaus import CorGaus
from nlme.corident import CorIdent
from nlme.corlin import CorLin
from nlme.cornatural import CorNatural
from nlme.corratio import CorRatio
from nlme.corspher import CorSpher
from nlme.corsymm import CorSymm
from nlme.pdmat import PdMat
from nlme.pdmat import Dim as _pd_mat_dim
from nlme.restruct import PdMatElement
from nlme.restruct import Dim as _pd_element_dim

_SPATIAL_CLASSES = (
    "corSpher",
    "corExp",
    "corGaus",
    "corLin",
    "corRatio",
)
_SPATIAL_TYPES = (CorExp, CorGaus, CorLin, CorRatio, CorSpher)
_R_CLASS = {
    CorSpher: "corSpher",
    CorExp: "corExp",
    CorGaus: "corGaus",
    CorLin: "corLin",
    CorRatio: "corRatio",
}
_CORSTRUCT_TYPES = (
    CorAR1,
    CorARMA,
    CorCAR1,
    CorCompSymm,
    CorIdent,
    CorNatural,
    CorSymm,
    CorExp,
    CorGaus,
    CorLin,
    CorRatio,
    CorSpher,
)


def Dim(object: Any, groups: Sequence[Any] | np.ndarray | None = None, **_ignored) -> Any:
    """Return the dimensions of ``object``; corStruct objects take a ``groups`` vector."""
    if isinstance(object, PdMat):
        return _pd_mat_dim(object)
    if isinstance(object, PdMatElement):
        return _pd_element_dim(object)
    if isinstance(object, _SPATIAL_TYPES):
        return _dim_corspatial(object, groups)
    if isinstance(object, _CORSTRUCT_TYPES):
        return corstruct.Dim(object, groups)
    return _dim_default(object)


def _dim_corspatial(object: Any, groups) -> dict[str, Any]:
    """``Dim.corSpatial``: the start offsets use pairs and the third entry is ``spClass``."""
    if groups is None:
        return getattr(object, "dim", None)
    val = corstruct.Dim(object, groups)
    lengths = np.asarray(val.len, dtype=np.int64)
    pairs = np.cumsum(lengths * (lengths - 1) // 2)[:-1]
    start = tuple(int(x) for x in np.concatenate([[0], pairs]))
    sp_class = _SPATIAL_CLASSES.index(_R_CLASS[type(object)]) + 1
    return {
        "N": val.N,
        "M": val.M,
        "spClass": sp_class,
        "sumLenSq": val.sum_len_sq,
        "len": val.len,
        "start": start,
    }


def _dim_default(object: Any) -> tuple[int, ...] | None:
    """``Dim.default``: ``dim(object)``, which is NULL (``None``) for a vector."""
    shape = np.shape(object)
    if len(shape) == 0:
        return None
    return tuple(int(x) for x in shape)
