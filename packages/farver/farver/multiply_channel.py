"""Multiply one channel of a colour string."""

from farver._common import modify_channels


def multiply_channel(colour, channel, value, space="rgb", white="D65", na_value=None):
    """Multiply ``channel`` by ``value`` and encode the colour again."""
    return modify_channels(colour, channel, value, space, white, na_value, 3)
