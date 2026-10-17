"""The vctrs size rule stringr uses before it calls stringi.

A length-1 vector recycles, including to length 0. Two other lengths must
agree. ``None`` is R's ``NULL`` and does not take part, which is why
``vec_size_common(NULL, 1:3)`` is 3 and ``vec_size_common(NULL)`` is 0.
"""

from __future__ import annotations

from stringi._na import is_na


class RecycleError(ValueError):
    """Raised when two vector lengths cannot share a size."""


def _size(value: object) -> int | None:
    if value is None:
        return None
    if is_na(value) or isinstance(value, (str, bool, int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    raise TypeError(f"cannot take the size of {type(value).__name__}")


def size_common(*values: object, names: list[str] | None = None) -> int:
    """Return the common size, or raise ``RecycleError``.

    The message names the vector that first set the size, then the later
    vector it cannot match. ``names`` are the R argument names; otherwise
    the labels are ``..1``, ``..2``, and so on.
    """

    common: int | None = None
    common_label = ""
    saw_one = False
    for index, value in enumerate(values):
        size = _size(value)
        if size is None:
            continue
        if names is not None and index < len(names):
            label = names[index]
        else:
            label = f"..{index + 1}"
        if size == 1:
            saw_one = True
            continue
        if common is None:
            common = size
            common_label = label
            continue
        if size == common:
            continue
        raise RecycleError(
            f"Can't recycle `{common_label}` (size {common}) to match `{label}` (size {size})."
        )
    if common is None:
        return 1 if saw_one else 0
    return common


def check_lengths(string: object, pattern: object, replacement: object = None) -> int:
    """``vctrs::vec_size_common(string, pattern, replacement)``."""

    return size_common(
        string,
        pattern,
        replacement,
        names=["string", "pattern", "replacement"],
    )


def no_boundary() -> None:
    raise ValueError("pattern can't be a boundary.")


def no_empty() -> None:
    raise ValueError('pattern can\'t be the empty string ("").')
