"""Read one channel from colour strings."""

from farver._common import get_channels


def get_channel(colour, channel, space="rgb", white="D65", na_value=None):
    """Return one channel. RGB channels are the byte values. Alpha is 0..1."""
    return get_channels(colour, channel, space, white, na_value)
