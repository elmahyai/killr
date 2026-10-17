"""Encode a colour matrix as hex strings."""

from farver._common import encode_colours


def encode_colour(colour, alpha=None, from_="rgb", white="D65"):
    """Encode colours as ``#RRGGBB`` or ``#RRGGBBAA``.

    ``from_`` is R's ``from``. A single alpha of ``NA`` or ``1/255`` is
    dropped. A single any other alpha is written on every colour, including
    fully opaque. A longer alpha drops the digits when that row is opaque.
    """
    return encode_colours(colour, alpha=alpha, from_=from_, white=white)
