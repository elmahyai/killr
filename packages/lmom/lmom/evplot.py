"""Extreme-value plot (lmom::evplot). R's S3 generic, with the default method only."""

from __future__ import annotations

from .evplot_default import evplot_default


def evplot(y=None, *args, **kwargs):
    """Dispatch to ``evplot_default``. Only the default method is translated."""
    return evplot_default(y, *args, **kwargs)
