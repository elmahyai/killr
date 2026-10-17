"""Numeric unit handling for the hexVP accessors. Helper, not a translated function.

R's accessors return grid unit objects unless `numeric = TRUE`, and convert between units with
the device size. Only the numeric result in the stored unit is translated here.
"""

from __future__ import annotations

import numpy as np


def numeric_in_unit(values, stored: str, ret_unit: str, numeric: bool, fname: str) -> np.ndarray:
    """Return `values` (held in `stored` units) as numbers in `ret_unit`, as `numeric = TRUE` does."""
    if not numeric:
        raise NotImplementedError(
            f"{fname}(numeric = FALSE) returns a grid unit object, which is not translated; use numeric=True"
        )
    if ret_unit != stored:
        raise NotImplementedError(
            f"converting {stored} to {ret_unit} needs grid's device size, which is not translated"
        )
    return np.array(values, dtype=np.float64)
