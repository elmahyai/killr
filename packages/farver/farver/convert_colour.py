"""Convert between colour spaces."""

from farver._common import convert_matrix


def convert_colour(colour, from_, to, white_from="D65", white_to=None):
    """Convert ``colour`` from one colour space to another.

    ``from_`` is R's ``from``. Rows are colours. CMYK uses four columns and
    every other space uses three. ``white_to`` defaults to ``white_from``.
    """
    return convert_matrix(colour, from_, to, white_from, white_to)
