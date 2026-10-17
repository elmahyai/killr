"""Generic ``lmList`` dispatch (nlme ``lmList``, ``lmList.groupedData``).

``lmList.formula`` is translated in ``nlme.lmlistformula``.  This module adds
the generic and the ``groupedData`` method, which reads the formula and the
data from the grouped object.
"""

from __future__ import annotations

import warnings
from typing import Any

from nlme.lmlistformula import _MISSING, LmList, lmList_formula


def lmList(
    object: Any,
    data: Any = None,
    level: Any = _MISSING,
    subset: Any = _MISSING,
    na_action: Any = _MISSING,
    pool: bool = True,
    warn_lm: bool = True,
) -> LmList:
    """List of ``lm`` fits by group for a formula or a groupedData object."""
    classes = getattr(object, "classes", ())
    if "groupedData" in classes:
        if data is not None:
            warnings.warn("'data' argument not used, but taken from groupedData object", stacklevel=2)
        return lmList_formula(
            object.formula,
            object,
            level=level,
            subset=subset,
            na_action=na_action,
            pool=pool,
            warn_lm=warn_lm,
        )
    if isinstance(object, str) and "~" in object:
        if data is None:
            raise ValueError("'data' is required when 'object' is a formula")
        return lmList_formula(
            object,
            data,
            level=level,
            subset=subset,
            na_action=na_action,
            pool=pool,
            warn_lm=warn_lm,
        )
    raise TypeError(f"no applicable method for 'lmList' applied to {type(object).__name__}")
