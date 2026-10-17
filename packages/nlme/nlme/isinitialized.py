"""Check whether nlme objects have been assigned values (nlme ``isInitialized``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.pdmat import PdMat
from nlme.restruct import PdMatElement, ReStruct


def isInitialized(object: Any) -> bool:
    """``pdMat``: ``length(object) > 0``.  ``reStruct``: all elements initialized."""
    if isinstance(object, ReStruct):
        return all(isInitialized(element) for _, element in object.blocks)
    if isinstance(object, (PdMat, PdMatElement)):
        return int(np.size(object.values)) > 0
    raise TypeError(f"no applicable method for 'isInitialized' applied to {type(object).__name__}")
