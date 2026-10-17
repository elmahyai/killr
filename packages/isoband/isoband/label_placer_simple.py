"""Label positions for a set of isolines, as R's ``label_placer_simple()`` in isoband 0.3.0.

``lines`` is a list of mappings with ``x``, ``y``, and ``id`` arrays (the output of
``isolines()``). ``labels_data`` is a mapping (or data frame) with the columns
``index``, ``break_index``, ``break_id``, and ``label``.

Indices are 1-based, as in R: ``index`` picks ``lines[index - 1]``, and
``break_index`` is only copied to the output. ``placer_fun(line_data, break_id)``
returns a mapping with ``x``, ``y``, and ``theta`` arrays for one line. The result
is a dict of arrays with the keys ``index``, ``break_index``, ``break_id``,
``label``, ``x``, ``y``, and ``theta``. R returns NULL when there are no label
rows; here that is an empty result.
"""

from __future__ import annotations

import math

import numpy as np

LABEL_COLUMNS = ("index", "break_index", "break_id", "label", "x", "y", "theta")


def empty_label_frame() -> dict[str, np.ndarray]:
    return {
        "index": np.zeros(0, dtype=np.int64),
        "break_index": np.zeros(0, dtype=np.int64),
        "break_id": np.zeros(0, dtype=object),
        "label": np.zeros(0, dtype=object),
        "x": np.zeros(0, dtype=np.float64),
        "y": np.zeros(0, dtype=np.float64),
        "theta": np.zeros(0, dtype=np.float64),
    }


def _is_missing(value) -> bool:
    if value is None:
        return True
    return isinstance(value, float) and math.isnan(value)


def _line_data(line) -> dict[str, np.ndarray]:
    return {
        "x": np.asarray(line["x"], dtype=np.float64).reshape(-1),
        "y": np.asarray(line["y"], dtype=np.float64).reshape(-1),
        "id": np.asarray(line["id"]).reshape(-1),
    }


def label_placer_simple(lines, labels_data, placer_fun) -> dict[str, np.ndarray]:
    index = np.asarray(labels_data["index"]).reshape(-1)
    break_index = np.asarray(labels_data["break_index"]).reshape(-1)
    break_id = np.asarray(labels_data["break_id"], dtype=object).reshape(-1)
    label = np.asarray(labels_data["label"], dtype=object).reshape(-1)

    pieces: list[dict[str, np.ndarray]] = []
    for k in range(index.size):
        line = _line_data(lines[int(index[k]) - 1])
        if line["x"].size == 0 or _is_missing(label[k]):
            continue
        pos = placer_fun(line, break_id[k])
        pos_x = np.asarray(pos["x"], dtype=np.float64).reshape(-1)
        n = pos_x.size
        if n == 0:
            continue
        pieces.append(
            {
                "index": np.full(n, index[k]),
                "break_index": np.full(n, break_index[k]),
                "break_id": np.full(n, break_id[k], dtype=object),
                "label": np.full(n, label[k], dtype=object),
                "x": pos_x,
                "y": np.asarray(pos["y"], dtype=np.float64).reshape(-1),
                "theta": np.asarray(pos["theta"], dtype=np.float64).reshape(-1),
            }
        )

    if not pieces:
        return empty_label_frame()
    return {name: np.concatenate([p[name] for p in pieces]) for name in LABEL_COLUMNS}
