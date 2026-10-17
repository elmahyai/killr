"""Raise one channel of a colour string to a lower bound."""

from farver._common import modify_channels


def raise_channel(colour, channel, value, space="rgb", white="D65", na_value=None):
    """Keep ``channel`` at least ``value`` and encode the colour again."""
    return modify_channels(colour, channel, value, space, white, na_value, 4)
