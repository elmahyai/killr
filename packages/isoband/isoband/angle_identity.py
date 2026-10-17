"""Label angles unchanged, as R's ``angle_identity()`` in isoband 0.3.0.

The returned adjuster gives back its input.
"""

from __future__ import annotations


def angle_identity():
    def adjust(x):
        return x

    return adjust
