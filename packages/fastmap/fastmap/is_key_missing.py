"""Test for a missing-key sentinel.

Translated from fastmap 1.2.0 ``is.key_missing`` in ``R/key_missing.R``.
"""

from __future__ import annotations

from fastmap.key_missing import KeyMissing


def is_key_missing(x):
    """Return whether ``x`` is a ``key_missing()`` sentinel."""
    return isinstance(x, KeyMissing)
