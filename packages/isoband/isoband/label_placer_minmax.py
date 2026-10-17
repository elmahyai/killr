"""Labels at the extremes of each isoline, as R's ``label_placer_minmax()`` in isoband 0.3.0.

``placement`` is a string with any of ``t`` (top), ``b`` (bottom), ``l`` (left), and
``r`` (right). For each letter the first point with that extreme value is used, in
the order top, bottom, left, right. The label sits at the mean of ``n`` points on
each side of that point, and its angle comes from the principal direction of those
points. A closed section (first point equal to last) wraps around. ``rot_adjuster``
defaults to ``angle_halfcircle_bottom()``.

Positions are 0-based inside this port; the outputs match R's values.
"""

from __future__ import annotations

import numpy as np

from isoband.angle_halfcircle_bottom import angle_halfcircle_bottom
from isoband.label_placer_simple import label_placer_simple


def _minmax_impl(x, y, ids, idx, n):
    idx_set = np.flatnonzero(ids == ids[idx])
    idx_min = int(idx_set.min())
    idx_max = int(idx_set.max())

    # Shift-invariant: the same arithmetic as R's 1-based version.
    if x[idx_min] == x[idx_max] and y[idx_min] == y[idx_max]:
        idx_range = idx_max - idx_min
        i = (np.arange(idx - n, idx + n + 1) - idx_min) % idx_range + idx_min
    else:
        i = np.arange(max(idx - n, idx_min), min(idx + n, idx_max) + 1)

    xs = x[i]
    ys = y[i]
    xave = xs.mean()
    yave = ys.mean()
    mat = np.column_stack([xs - xave, ys - yave])
    vh = np.linalg.svd(mat, full_matrices=False)[2]
    return xave, yave, np.arctan2(vh[0, 1], vh[0, 0])


def label_placer_minmax(placement="tb", rot_adjuster=None, n=2):
    adjust = rot_adjuster if rot_adjuster is not None else angle_halfcircle_bottom()

    def placer_fun(line_data, *args):
        x = line_data["x"]
        y = line_data["y"]
        ids = line_data["id"]

        found = []
        if "t" in placement:
            found.append(np.flatnonzero(y == y.max()))
        if "b" in placement:
            found.append(np.flatnonzero(y == y.min()))
        if "l" in placement:
            found.append(np.flatnonzero(x == x.min()))
        if "r" in placement:
            found.append(np.flatnonzero(x == x.max()))
        idx = [int(hits[0]) for hits in found if hits.size > 0]

        xs, ys, thetas = [], [], []
        for k in idx:
            xa, ya, ta = _minmax_impl(x, y, ids, k, n)
            xs.append(xa)
            ys.append(ya)
            thetas.append(ta)
        return {
            "x": np.asarray(xs, dtype=np.float64),
            "y": np.asarray(ys, dtype=np.float64),
            "theta": adjust(np.asarray(thetas, dtype=np.float64)),
        }

    def place(lines, labels_data):
        return label_placer_simple(lines, labels_data, placer_fun)

    return place
