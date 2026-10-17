"""Binary operators that call the finished join routines.

``s_times`` and ``stri_times`` are ``stri_dup``. ``s_plus`` and ``stri_plus``
are ``stri_join`` of two strings with an empty separator, which is what
``C_stri_join2`` does. Missing characters stay missing.
"""

from __future__ import annotations

from stringi.join import stri_dup, stri_join


def s_times(e1, e2):
    """Duplicate each string the given number of times.

    This is ``%s*%``. A missing string or a missing count stays missing.
    """

    return stri_dup(e1, e2)


stri_times = s_times


def s_plus(e1, e2):
    """Concatenate two character vectors with an empty separator.

    This is ``%s+%``. It calls ``stri_join`` with ``sep=""``. A missing
    element stays missing, and a length-zero argument makes the result empty.
    """

    return stri_join(e1, e2, sep="")


stri_plus = s_plus
