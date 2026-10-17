"""Distance between colours."""

from farver._common import compare_matrices


def compare_colour(
    colour_from,
    colour_to=None,
    from_space=None,
    to_space=None,
    method="euclidean",
    white_from="D65",
    white_to=None,
    lightness=2,
    chroma=1,
):
    """Compare colours. Omitting ``colour_to`` compares a set with itself.

    Only the strict upper triangle is filled in that case. The rest is zero.
    """
    if from_space is None:
        raise ValueError("Unknown colour space")
    if to_space is None:
        to_space = from_space
    if white_to is None:
        white_to = white_from
    symmetric = colour_to is None
    if symmetric:
        colour_to = colour_from
    return compare_matrices(
        colour_from,
        colour_to,
        from_space,
        to_space,
        method,
        white_from,
        white_to,
        lightness,
        chroma,
        symmetric,
    )
