"""The S4 classes of hexbin, as Python classes that hold the same slots.

The R method bodies are ordinary functions in this package. Dispatch is not copied:
callers use `isinstance` where R uses `is()` or `inherits()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ._r import NA_INTEGER

__all__ = ["HexBin", "ErodeBin", "SmoothBin", "HexBinList", "HexVP", "NA_INTEGER", "base_slots"]


def _empty_int() -> np.ndarray:
    return np.zeros(0, dtype=np.int32)


@dataclass
class HexBin:
    """Slots of the R class `hexbin`."""

    cell: np.ndarray  # integer, 1-based ids of the non-empty cells
    count: np.ndarray  # numeric counts, one per cell
    xcm: np.ndarray
    ycm: np.ndarray
    xbins: float
    shape: float
    xbnds: np.ndarray
    ybnds: np.ndarray
    dimen: np.ndarray  # c(rows, columns)
    n: int  # number of points used
    ncells: int  # number of non-empty cells
    call: Any = None  # R's match.call(); not reproduced, left None
    xlab: Any = ""
    ylab: Any = ""
    cID: np.ndarray | None = None  # per-point cell ids, with NA_INTEGER for NA points
    cAtt: np.ndarray = field(default_factory=_empty_int)


@dataclass
class ErodeBin(HexBin):
    """Slots of the R class `erodebin`, which extends `hexbin`."""

    cdfcut: float = 0.5
    eroded: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))
    erode: np.ndarray = field(default_factory=_empty_int)


@dataclass
class SmoothBin(HexBin):
    """Slots of the R class `smoothbin`, which extends `hexbin`."""

    wts: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float64))


@dataclass
class HexBinList:
    """Slots of the R class `hexbinList`."""

    n: int
    hbins: list
    Xbnds: np.ndarray
    Ybnds: np.ndarray
    Xbins: Any  # a scalar in list2hexList, a zero vector in hexList (as R)
    Shape: float
    Bnames: list
    CntBnds: np.ndarray


@dataclass
class HexVP:
    """Numeric slots of the R class `hexVP`, as the accessors read them.

    R keeps `mar` and `plt` as grid units: `mar` in lines and `plt` in npc, the units
    `hexViewport()` stores. Grid unit conversion is not translated, so a value is only returned
    in the unit it is stored in. The R viewport objects `hexVp.on` and `hexVp.off` are not held.
    """

    mar: np.ndarray
    plt: np.ndarray
    xscale: np.ndarray
    yscale: np.ndarray
    shape: float
    mar_unit: str = "lines"
    plt_unit: str = "npc"


_BASE_NAMES = (
    "cell",
    "count",
    "xcm",
    "ycm",
    "xbins",
    "shape",
    "xbnds",
    "ybnds",
    "dimen",
    "n",
    "ncells",
    "call",
    "xlab",
    "ylab",
    "cID",
    "cAtt",
)


def base_slots(hbin: HexBin) -> dict:
    """The `hexbin` slots of any hexbin-like object, for `new("x", hbin, ...)` style copies."""
    return {name: getattr(hbin, name) for name in _BASE_NAMES}
