"""Labels at the middle of each isoline section, as R's ``label_placer_middle()`` in isoband 0.3.0.

Each section is the points with ``id == i`` for ``i = 1, 2, ...``, one per distinct
id in the line, as R does. The label sits at the middle point. Its angle comes from
the principal direction of the three points around it, then ``rot_adjuster``
(default ``angle_halfcircle_bottom()``) is applied.

A section must have at least 2 points. R reads ``x[0]`` for shorter sections and
gives an undefined result there, so this port raises ``ValueError``.
"""

from __future__ import annotations

import numpy as np

from isoband.angle_halfcircle_bottom import angle_halfcircle_bottom
from isoband.label_placer_simple import label_placer_simple


def label_placer_middle(rot_adjuster=None):
    adjust = rot_adjuster if rot_adjuster is not None else angle_halfcircle_bottom()

    def placer_fun(line_data, *args):
        ids = line_data["id"]
        x_all = line_data["x"]
        y_all = line_data["y"]
        n_sections = np.unique(ids).size
        xs, ys, thetas = [], [], []
        for i in range(1, n_sections + 1):
            mask = ids == i
            x = x_all[mask]
            y = y_all[mask]
            m = x.size // 2  # R's as.integer(length(x) / 2), 1-based
            if m < 1:
                raise ValueError("label_placer_middle needs at least 2 points per section")
            # 1-based positions m - 1, m, m + 1; position 0 does not exist in R.
            keep = [j for j in (m - 1, m, m + 1) if j >= 1]
            xt = np.array([x[j - 1] for j in keep], dtype=np.float64)
            yt = np.array([y[j - 1] for j in keep], dtype=np.float64)
            mat = np.column_stack([xt - xt.mean(), yt - yt.mean()])
            vh = np.linalg.svd(mat, full_matrices=False)[2]
            xs.append(x[m - 1])
            ys.append(y[m - 1])
            thetas.append(np.arctan2(vh[0, 1], vh[0, 0]))
        return {
            "x": np.asarray(xs, dtype=np.float64),
            "y": np.asarray(ys, dtype=np.float64),
            "theta": adjust(np.asarray(thetas, dtype=np.float64)),
        }

    def place(lines, labels_data):
        return label_placer_simple(lines, labels_data, placer_fun)

    return place
