"""A sentinel for a key that is not in a map, queue, or stack.

Translated from fastmap 1.2.0 ``key_missing`` in ``R/key_missing.R``.
"""

from __future__ import annotations


class KeyMissing:
    """The object ``key_missing()`` returns.

    Two sentinels compare equal. Printing one shows ``<Key Missing>``.
    """

    def __eq__(self, other):
        return isinstance(other, KeyMissing)

    def __hash__(self):
        return hash(KeyMissing)

    def __repr__(self):
        return "<Key Missing>"

    def __str__(self):
        return "<Key Missing>"


def key_missing():
    """Return a missing-key sentinel.

    Pass it as ``missing_default`` so ``get``, ``remove``, ``pop``, and
    ``peek`` can tell a missing entry from a stored ``None``.
    """
    return KeyMissing()
