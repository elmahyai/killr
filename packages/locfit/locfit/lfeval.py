"""Evaluation component of a fit: translation of locfit 1.5-9.12 ``lfeval``."""

from __future__ import annotations

from ._common import field


def lfeval(object):
    """Return ``object$eva``, the evaluation record of a fit."""
    return field(object, "eva")


__all__ = ["lfeval"]
