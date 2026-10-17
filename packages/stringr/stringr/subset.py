"""Keep the elements of ``string`` that match a pattern.

``str_subset`` is ``string[str_detect(string, pattern)]`` after missing
matches are dropped. The index is the detection vector, and the values
come from the original ``string``. A true match past the end of that
string is a missing value. Empty and boundary patterns are rejected by
:func:`stringr.detect.str_detect`.
"""

from __future__ import annotations

from stringi._na import NA, is_na

from stringr.detect import _Named, str_detect


def _elements(string: object) -> list:
    if is_na(string) or isinstance(string, str):
        return [string]
    if isinstance(string, (list, tuple)):
        return list(string)
    raise TypeError("string must be a character vector.")


def str_subset(string, pattern, negate: bool = False):
    """Elements of ``string`` that match ``pattern``.

    A missing string never matches. Names of the retained elements are
    kept. When the detection vector is longer than ``string``, a selected
    position past the end is ``NA``.
    """

    found = str_detect(string, pattern, negate=negate)
    values = _elements(string)
    names = getattr(string, "names", None)
    chosen = []
    chosen_names = []
    size = len(values)
    for index, flag in enumerate(found):
        if flag is not True:
            continue
        if index < size:
            chosen.append(values[index])
            if names is not None:
                chosen_names.append(names[index] if index < len(names) else NA)
        else:
            chosen.append(NA)
            if names is not None:
                chosen_names.append(NA)
    if names is None:
        return chosen
    return _Named(chosen, chosen_names)
