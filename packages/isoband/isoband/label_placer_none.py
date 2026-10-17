"""No labels, as R's ``label_placer_none()`` in isoband 0.3.0.

The returned placer takes ``(lines, labels_data)`` and gives an empty result.
"""

from __future__ import annotations

from isoband.label_placer_simple import empty_label_frame


def label_placer_none():
    def place(*args, **kwargs):
        return empty_label_frame()

    return place
