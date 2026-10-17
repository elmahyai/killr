"""Decode hex colours and colour names."""

from farver._common import decode_colours


def decode_colour(colour, alpha=False, to="rgb", white="D65", na_value=None):
    """Decode hex strings or colour names into a colour matrix.

    ``alpha=True`` is R's ``isTRUE``: only a real true value adds the column.
    RGB without alpha is the channel integers. Other spaces are floating point.
    """
    return decode_colours(colour, alpha=alpha, to=to, white=white, na_value=na_value)
