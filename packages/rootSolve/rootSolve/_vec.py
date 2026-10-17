"""Numeric vectors and the matrices the derivative routines return."""

import math

import numpy as np


class Vector:
    """A numeric vector. Names are optional and follow R's name attribute."""

    def __init__(self, values, names=None):
        if isinstance(values, Vector):
            self.values = list(values.values)
            self.names = list(values.names) if values.names is not None else None
            if names is not None:
                self.names = list(names)
            return
        if isinstance(values, dict):
            self.names = list(values.keys())
            self.values = [float(item) for item in values.values()]
            return
        self.values = [_as_float(item) for item in values]
        self.names = list(names) if names is not None else None
        if self.names is not None and len(self.names) != len(self.values):
            raise ValueError("names and values have different lengths")

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, item):
        if isinstance(item, str):
            return self.values[self.names.index(item)]
        return self.values[item]

    def __setitem__(self, item, value):
        if isinstance(item, str):
            self.values[self.names.index(item)] = _as_float(value)
        else:
            self.values[item] = _as_float(value)

    def copy(self):
        return Vector(self.values, self.names)


def _as_float(value):
    if isinstance(value, bool) or value is None:
        raise TypeError("not numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("not numeric") from exc
    return number


def as_vector(x, what):
    """Require a numeric vector. ``what`` is ``x`` or ``y`` in the error."""
    try:
        return Vector(x)
    except TypeError as exc:
        raise ValueError(f"{what}-values should be numeric") from exc


def perturb(value, pert=1e-8):
    """pmax(abs(value) * pert, pert). Names are kept."""
    vector = Vector(value)
    vector.values = [max(abs(item) * pert, pert) for item in vector.values]
    return vector


def unlist(value):
    """Flatten a number, a sequence, or a list of either, the way unlist does."""
    if isinstance(value, Vector):
        return list(value.values), list(value.names) if value.names else None
    if isinstance(value, bool) or value is None:
        raise TypeError("not numeric")
    if isinstance(value, (int, float, np.floating)):
        return [float(value)], None
    if isinstance(value, np.ndarray):
        return [float(item) for item in np.ravel(value, order="F")], None
    if isinstance(value, (list, tuple)):
        values = []
        names = []
        named = False
        for item in value:
            part, part_names = unlist(item)
            values.extend(part)
            if part_names:
                named = True
                names.extend(part_names)
            else:
                names.extend([None] * len(part))
        return values, names if named else None
    if isinstance(value, dict):
        return [float(item) for item in value.values()], list(value.keys())
    raise TypeError("not numeric")


def column_major(matrix):
    """Values of a matrix in R's column-major order."""
    array = np.asarray(matrix, dtype=float)
    return np.ravel(array, order="F")


class Matrix:
    """A numeric matrix with optional dimnames."""

    def __init__(self, data, rownames=None, colnames=None):
        self.data = np.array(data, dtype=float, copy=True)
        self.rownames = list(rownames) if rownames else None
        self.colnames = list(colnames) if colnames else None

    @property
    def shape(self):
        return self.data.shape

    def __str__(self):
        rows, cols = self.data.shape
        body = []
        for row in range(rows):
            numbers = " ".join(f"{self.data[row, col]:.8g}" for col in range(cols))
            label = ""
            if self.rownames:
                label = f"{self.rownames[row]} "
            body.append(label + numbers)
        header = ""
        if self.colnames:
            header = " ".join(self.colnames)
            if self.rownames:
                header = " " + header
            header += "\n"
        return header + "\n".join(body)
