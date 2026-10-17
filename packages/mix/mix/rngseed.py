"""`rngseed` of mix 1.0-13 (R/mix.R): seeds the Park-Miller generator of the kernel."""

from __future__ import annotations

from . import _kernel as K


def rngseed(seed) -> None:
    seed = int(seed)  # as.integer truncates
    if seed <= 0:
        raise ValueError("'seed' must be a positive integer")
    K.rngs(seed)
