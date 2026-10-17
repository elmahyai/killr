"""Turn raw command output into lines, the way readLines does."""

import warnings


def as_text(x, n=None, encoding="utf-8"):
    """Split a raw vector into lines.

    A value that does not end in a newline warns
    ``incomplete final line found on 'x'``.
    """
    if x is None or len(x) == 0:
        return []
    if isinstance(x, str):
        data = x.encode("utf-8")
    else:
        data = bytes(x)
    if not data.endswith(b"\n"):
        warnings.warn("incomplete final line found on 'x'", stacklevel=2)
    text = data.decode(encoding if encoding not in (None, "unknown", "") else "utf-8")
    lines = text.splitlines()
    if n is not None:
        lines = lines[: int(n)]
    return lines
