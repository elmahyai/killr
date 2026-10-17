"""Set one channel of a colour string."""

from farver._common import modify_channels


def set_channel(colour, channel, value, space="rgb", white="D65", na_value=None):
    """Replace ``channel`` with ``value`` and encode the colour again."""
    return modify_channels(colour, channel, value, space, white, na_value, 1)
