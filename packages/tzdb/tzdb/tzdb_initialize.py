"""Initialize tzdb for use from another package.

The function returns nothing. Loading the package is what sets the path to
the text time zone database.
"""


def tzdb_initialize():
    """Return ``None``.

    R returns ``NULL`` invisibly. The call exists so that loading this
    package runs the same setup as tzdb's ``.onLoad``.
    """
    return None
