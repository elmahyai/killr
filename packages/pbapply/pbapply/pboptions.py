"""Get and set progress-bar options the way pbapply::pboptions does."""

from __future__ import annotations

from collections.abc import Mapping
import importlib
from typing import Any

_startpb = importlib.import_module("pbapply.startpb")


def pboptions(
    options: Mapping[str, Any] | None = None,
    /,
    **kwargs: Any,
) -> dict[str, Any]:
    """Return former pboptions; optionally replace or merge tagged settings."""
    opar = dict(_startpb._pboptions)
    if options is not None:
        if kwargs:
            raise TypeError("pboptions() takes either a mapping or keyword arguments")
        _startpb._pboptions.clear()
        _startpb._pboptions.update(dict(options))
        return opar
    if kwargs:
        npar = dict(opar)
        for name, value in kwargs.items():
            if name not in npar:
                raise ValueError("NAs are not allowed in subscripted assignments")
            if value is None and name == "type":
                npar[name] = None
            else:
                npar[name] = value
        _startpb._pboptions.clear()
        _startpb._pboptions.update(npar)
    return opar
