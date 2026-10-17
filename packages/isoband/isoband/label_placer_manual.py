"""Labels at given positions, as R's ``label_placer_manual()`` in isoband 0.3.0.

``breaks``, ``x``, ``y``, and ``theta`` are recycled to a common length, as R's
``rep_len()`` does. A label is placed where its ``break_id`` equals a value in
``breaks``. Numeric breaks are compared as text with up to 15 significant digits,
as R's ``as.character()`` does.
"""

from __future__ import annotations

import numpy as np

from isoband.label_placer_simple import label_placer_simple


def _as_character(values) -> np.ndarray:
    arr = np.asarray(values).reshape(-1)
    if arr.dtype.kind in "USO":
        return np.asarray([str(v) for v in arr], dtype=object)
    return np.asarray([f"{float(v):.15g}" for v in arr], dtype=object)


def label_placer_manual(breaks, x, y, theta):
    breaks_arr = _as_character(breaks)
    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    theta_arr = np.asarray(theta, dtype=np.float64).reshape(-1)

    n = max(breaks_arr.size, x_arr.size, y_arr.size, theta_arr.size)
    breaks_arr = np.resize(breaks_arr, n)
    x_arr = np.resize(x_arr, n)
    y_arr = np.resize(y_arr, n)
    theta_arr = np.resize(theta_arr, n)

    def placer_fun(line_data, break_id):
        idx = breaks_arr == str(break_id)
        return {"x": x_arr[idx], "y": y_arr[idx], "theta": theta_arr[idx]}

    def place(lines, labels_data):
        return label_placer_simple(lines, labels_data, placer_fun)

    return place
