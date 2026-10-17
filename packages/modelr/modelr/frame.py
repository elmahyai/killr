"""Data frames and factors for modelr.

A frame is a dict of columns in insertion order. A factor keeps its
levels. Row indexes that cross the R boundary stay 1-based.
"""

from __future__ import annotations


class Factor:
    """A vector of labels with a fixed level order."""

    def __init__(self, values, levels, ordered=False):
        self.values = list(values)
        self.levels = list(levels)
        self.ordered = bool(ordered)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]

    def take(self, positions):
        """positions are 0-based."""
        return Factor([self.values[i] for i in positions], self.levels, self.ordered)


class Frame:
    """Named columns of equal length."""

    def __init__(self, columns):
        self.columns = {}
        nrow = None
        for name, values in columns.items():
            if isinstance(values, Factor):
                stored = values
                length = len(values)
            elif isinstance(values, str):
                raise TypeError("a column must be a sequence, not a string")
            else:
                stored = list(values)
                length = len(stored)
            if nrow is None:
                nrow = length
            elif length != nrow:
                raise ValueError("column lengths must match")
            self.columns[str(name)] = stored
        self.nrow = 0 if nrow is None else nrow

    def __len__(self):
        return self.nrow

    def __getitem__(self, name):
        return self.columns[name]

    @property
    def ncol(self):
        return len(self.columns)

    def names(self):
        return list(self.columns)

    def copy(self):
        copied = {}
        for name, values in self.columns.items():
            if isinstance(values, Factor):
                copied[name] = Factor(values.values, values.levels, values.ordered)
            else:
                copied[name] = list(values)
        return Frame(copied)

    def with_column(self, name, values):
        out = self.copy()
        stored = values if isinstance(values, Factor) else list(values)
        if len(stored) != out.nrow:
            raise ValueError("column lengths must match")
        out.columns[str(name)] = stored
        return out

    def subset(self, idx):
        """Keep rows at 1-based positions. Repeats are kept."""
        positions = [i - 1 for i in idx]
        cols = {}
        for name, values in self.columns.items():
            if isinstance(values, Factor):
                cols[name] = values.take(positions)
            else:
                cols[name] = [values[i] for i in positions]
        return Frame(cols)


def is_na(value):
    if value is None:
        return True
    if isinstance(value, float):
        return value != value
    return False


def as_floats(column):
    """Numeric column as floats. Missing values are NaN."""
    if isinstance(column, Factor):
        raise TypeError("a factor is not numeric")
    out = []
    for value in column:
        if is_na(value):
            out.append(float("nan"))
        elif isinstance(value, bool):
            out.append(1.0 if value else 0.0)
        else:
            out.append(float(value))
    return out


def as_frame(data):
    if isinstance(data, Frame):
        return data
    if hasattr(data, "as_frame"):
        return data.as_frame()
    if isinstance(data, dict):
        return Frame(data)
    raise ValueError("`data` must be a data frame.")
