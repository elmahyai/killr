"""Cap one channel of a colour string at an upper bound."""

from farver._common import modify_channels


def cap_channel(colour, channel, value, space="rgb", white="D65", na_value=None):
    """Keep ``channel`` at most ``value`` and encode the colour again."""
    return modify_channels(colour, channel, value, space, white, na_value, 5)
