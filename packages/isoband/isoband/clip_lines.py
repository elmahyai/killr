"""Clip lines so they do not run into boxes, as R's ``clip_lines()`` in isoband 0.3.0.

``clip_boxes`` is a table with columns ``x``, ``y``, ``width``, ``height``, and ``theta``
(theta in radians), one row per box. Any mapping or data frame with those keys works.
The boxes are applied in order. The result is a dict with ``x``, ``y``, and ``id``.
"""

from __future__ import annotations

import numpy as np
from isoband_kernel import clip_lines_kernel

_BOX_COLUMNS = ("x", "y", "width", "height", "theta")


def clip_lines(x, y, id, clip_boxes, asp: float = 1.0) -> dict[str, np.ndarray]:
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    id_arr = np.asarray(id).reshape(-1).astype(np.int32)
    columns = [np.asarray(clip_boxes[name], dtype=np.float64).reshape(-1) for name in _BOX_COLUMNS]
    n_boxes = columns[0].size
    if n_boxes == 0:
        raise ValueError("clip_boxes must have at least one row")
    if any(col.size != n_boxes for col in columns):
        raise ValueError("clip_boxes columns must all have the same length")
    boxes = np.ascontiguousarray(np.column_stack(columns), dtype=np.float64)
    xs, ys, ids = clip_lines_kernel(x_arr, y_arr, id_arr, boxes, float(asp))
    return {"x": xs, "y": ys, "id": ids}
