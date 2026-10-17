"""Frailty term dispatcher (survival::frailty)."""

from __future__ import annotations

from typing import Any

from survival.frailty_gamma import GammaFrailtyPenalty, frailty_gamma
from survival.frailty_gaussian import GaussianFrailtyPenalty, frailty_gaussian
from survival.frailty_t import TFrailtyPenalty, frailty_t

_DISTRIBUTIONS = ("gamma", "gaussian", "t")

_DISPATCH = {
    "gamma": frailty_gamma,
    "gaussian": frailty_gaussian,
    "t": frailty_t,
}


def _pmatch(value: Any, choices: tuple[str, ...]) -> int | None:
    """R ``pmatch`` for a single string against ``choices`` (1-based index or ``None``)."""
    if not isinstance(value, str):
        return None
    matches = [index for index, choice in enumerate(choices) if choice.startswith(value)]
    if len(matches) == 1:
        return matches[0] + 1
    return None


def frailty(
    x: Any,
    distribution: str = "gamma",
    **kwargs: Any,
) -> GammaFrailtyPenalty | GaussianFrailtyPenalty | TFrailtyPenalty:
    """Build a frailty penalty term; dispatches to gamma, Gaussian, or t."""
    index = _pmatch(distribution, _DISTRIBUTIONS)
    if index is not None:
        distribution = _DISTRIBUTIONS[index - 1]

    impl = _DISPATCH.get(distribution)
    if impl is None:
        raise ValueError(f"Function 'frailty.{distribution}' not found")

    return impl(x, **kwargs)
