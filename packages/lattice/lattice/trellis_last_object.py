"""Retrieve the last saved trellis object (``trellis.last.object`` in lattice 0.23-1)."""

from __future__ import annotations

import warnings
from typing import Any

from lattice.lattice_status import lattice_get_status


def trellis_last_object(*, prefix: str | None = None, **update_kwargs: Any) -> Any:
    """Return the trellis object saved during the last print, optionally updated."""
    if prefix is None:
        prefix = lattice_get_status("current.prefix")
    if not lattice_get_status("current.plot.saved", prefix=prefix):
        warnings.warn("Requested 'trellis' object was not saved")
        return None
    ans = lattice_get_status("last.object", prefix=prefix)
    if update_kwargs:
        raise NotImplementedError("update.trellis is not translated")
    return ans
