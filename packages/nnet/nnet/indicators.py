"""Class indicators and the position of the maximum, from nnet."""

from __future__ import annotations


def which_is_max(x):
    """1-based index of the unique maximum.

    Several maxima make R draw one index with sample. This returns the
    smallest index.
    """
    values = list(x)
    if not values:
        raise ValueError("x is empty")
    best = max(values)
    winners = [index + 1 for index, value in enumerate(values) if value == best]
    return winners[0]


def class_ind(cl):
    """One column per class, in the order R's factor sorts the labels."""
    labels = [str(item) for item in cl]
    levels = sorted(set(labels))
    columns = []
    for level in levels:
        columns.append([1.0 if label == level else 0.0 for label in labels])
    rows = list(zip(*columns)) if columns else []
    flat = []
    for column in columns:
        flat.extend(column)
    return flat, levels, [list(row) for row in rows]
