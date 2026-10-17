"""Cartesian, polar, and spherical coordinates."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.elementary import hypot
from pracma.num_helpers import require_numeric


def _parts(values, name, widths):
    require_numeric(values, name)
    array = np.asarray(values, dtype=float)
    if array.ndim <= 1 and array.size in widths:
        return [array.reshape(-1)[i] for i in range(array.size)], 1, int(array.size), True
    if array.ndim == 2 and array.shape[1] in widths:
        columns = [array[:, i] for i in range(array.shape[1])]
        return columns, int(array.shape[0]), int(array.shape[1]), False
    raise PracmaError("Input must be a vector of length 3 or a matrix with 3 columns.")


def _pack(columns, rows, vector):
    if vector:
        return np.array([float(np.asarray(column).reshape(-1)[0]) for column in columns])
    return np.column_stack(columns)


def cart2sph(xyz):
    columns, rows, _, vector = _parts(xyz, "xyz", (3,))
    x, y, z = columns
    hypotxy = hypot(x, y)
    radius = hypot(hypotxy, z)
    phi = np.arctan2(z, hypotxy)
    theta = np.arctan2(y, x)
    return _pack((theta, phi, radius), rows, vector)


def sph2cart(tpr):
    columns, rows, _, vector = _parts(tpr, "tpr", (3,))
    theta, phi, radius = columns
    z = radius * np.sin(phi)
    tmp = radius * np.cos(phi)
    x = tmp * np.cos(theta)
    y = tmp * np.sin(theta)
    return _pack((x, y, z), rows, vector)


def cart2pol(xyz):
    columns, rows, count, vector = _parts(xyz, "xyz", (2, 3))
    x, y = columns[0], columns[1]
    phi = np.arctan2(y, x)
    radius = hypot(x, y)
    if count == 2:
        return _pack((phi, radius), rows, vector)
    return _pack((phi, radius, columns[2]), rows, vector)


def pol2cart(prz):
    columns, rows, count, vector = _parts(prz, "prz", (2, 3))
    phi, radius = columns[0], columns[1]
    x = radius * np.cos(phi)
    y = radius * np.sin(phi)
    if count == 2:
        return _pack((x, y), rows, vector)
    return _pack((x, y, columns[2]), rows, vector)
