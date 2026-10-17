"""Case mapping for stringr 1.6.0.

``str_to_lower``, ``str_to_upper``, ``str_to_title``, and
``str_to_sentence`` call the finished stringi case functions. The English
locale is the default, matching the R wrappers. ``str_to_camel``,
``str_to_snake``, and ``str_to_kebab`` split words with the same ICU
pattern as ``to_words`` and then call those case and trim functions.

A character vector is a list. One string is a list of length one. A
missing string is ``stringi._na.NA``.
"""

from __future__ import annotations

import math

from rlang import Named
from stringi import (
    stri_opts_brkiter,
    stri_opts_fixed,
    stri_replace_all_fixed,
    stri_replace_all_regex,
    stri_sub,
    stri_sub_assign,
    stri_trans_tolower,
    stri_trans_totitle,
    stri_trans_toupper,
)
from stringi._na import is_na


_BREAKS = (
    r"[^\p{L}\p{N}]+"
    r"|(?<=\p{Ll})(?=\p{Lu})"
    r"|(?<=\p{L})(?=\p{N})"
    r"|(?<=\p{N})(?=\p{L})"
    r"|(?<=\p{Lu})(?=\p{Lu}\p{Ll})"
)


def as_list(value):
    """A stringi result as a list. One string comes back bare."""

    if isinstance(value, list):
        return value
    return [value]


def vector_length(value) -> int:
    if value is None:
        return 0
    if is_na(value) or isinstance(value, (str, bool, int, float)):
        return 1
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def copy_names(source, result):
    """Keep names when the result has the same length as ``source``."""

    names = getattr(source, "names", None)
    if not names or len(names) != len(result):
        return result
    return Named(list(result), list(names))


def check_string(value, arg: str = "locale") -> None:
    """``rlang::check_string``: one string, empty allowed, missing rejected."""

    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = value[0]
        else:
            raise ValueError(f"`{arg}` must be a single string.")
    if is_na(value) or not isinstance(value, str):
        raise ValueError(f"`{arg}` must be a single string.")


def check_bool(value, arg: str = "value") -> None:
    """``rlang::check_bool``: exactly ``True`` or ``False``."""

    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = value[0]
        else:
            raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`.")
    if value is True or value is False:
        return
    raise ValueError(f"`{arg}` must be `TRUE` or `FALSE`.")


def check_character(value, arg: str = "string") -> None:
    """``rlang::check_character``. ``NA`` is allowed. ``None`` is not."""

    if is_na(value) or isinstance(value, str):
        return
    if isinstance(value, (list, tuple)) and all(
        is_na(item) or isinstance(item, str) for item in value
    ):
        return
    raise ValueError(f"`{arg}` must be a character vector.")


def check_number_whole(value, arg: str = "width") -> None:
    """One finite whole number. ``4.0`` is whole. ``4.2`` is not."""

    if isinstance(value, bool) or isinstance(value, (list, tuple)):
        raise ValueError(f"`{arg}` must be a whole number.")
    if isinstance(value, int):
        return
    if isinstance(value, float) and math.isfinite(value) and value == math.trunc(value):
        return
    raise ValueError(f"`{arg}` must be a whole number.")


def check_number_decimal(value, arg: str = "width") -> None:
    """One number. Infinity is allowed. A missing value is not."""

    if isinstance(value, bool) or isinstance(value, (list, tuple)):
        raise ValueError(f"`{arg}` must be a number.")
    if isinstance(value, int):
        return
    if isinstance(value, float) and value == value:
        return
    raise ValueError(f"`{arg}` must be a number.")


def arg_match(value, choices: tuple[str, ...], arg: str) -> str:
    """``rlang::arg_match``. An exact choice, or the full default vector.

    A unique prefix is not a match. The default ``c("left", "right")``
    arrives as that whole vector and selects the first choice.
    """

    if isinstance(value, (list, tuple)):
        if len(value) == len(choices) and set(value) == set(choices):
            return choices[0]
        shown = ", ".join(repr(item) for item in value)
        raise ValueError(f"`{arg}` must be one of {', '.join(repr(item) for item in choices)}, not {shown}.")
    if isinstance(value, str) and value in choices:
        return value
    raise ValueError(
        f"`{arg}` must be one of {', '.join(repr(item) for item in choices)}, not {value!r}."
    )


def _replace_regex(string, pattern: str, replacement: str):
    return as_list(
        stri_replace_all_regex(string, pattern, replacement, vectorize_all=True)
    )


def _replace_fixed(string, pattern: str, replacement: str):
    options = stri_opts_fixed(case_insensitive=False)
    return as_list(
        stri_replace_all_fixed(
            string,
            pattern,
            replacement,
            vectorize_all=True,
            opts_fixed=options,
        )
    )


def _to_words(string):
    from stringr.trim import str_trim

    out = _replace_regex(string, _BREAKS, " ")
    out = str_to_lower(out)
    return str_trim(out)


def str_to_upper(string, locale: str = "en"):
    """Convert to upper case. The default locale is English."""

    check_string(locale, "locale")
    out = as_list(stri_trans_toupper(string, locale=locale))
    return copy_names(string, out)


def str_to_lower(string, locale: str = "en"):
    """Convert to lower case. The default locale is English."""

    check_string(locale, "locale")
    out = as_list(stri_trans_tolower(string, locale=locale))
    return copy_names(string, out)


def str_to_title(string, locale: str = "en"):
    """Capitalize the first letter of each word. The default locale is English."""

    check_string(locale, "locale")
    options = stri_opts_brkiter(locale=locale)
    out = as_list(stri_trans_totitle(string, opts_brkiter=options))
    return copy_names(string, out)


def str_to_sentence(string, locale: str = "en"):
    """Capitalize the first letter of each sentence. The default locale is English."""

    check_string(locale, "locale")
    options = stri_opts_brkiter(type="sentence", locale=locale)
    out = as_list(stri_trans_totitle(string, opts_brkiter=options))
    return copy_names(string, out)


def str_to_camel(string, first_upper: bool = False):
    """Camel case. The first letter stays lower unless ``first_upper`` is true."""

    check_character(string, "string")
    check_bool(first_upper, "first_upper")
    out = _replace_fixed(str_to_title(_to_words(string)), " ", "")
    if not first_upper and out:
        first = str_to_lower(as_list(stri_sub(out, from_=1, to=1)))
        out = as_list(stri_sub_assign(out, from_=1, to=1, value=first))
    return copy_names(string, out)


def str_to_snake(string):
    """Snake case: lower case words separated by underscores."""

    check_character(string, "string")
    return copy_names(string, _replace_fixed(_to_words(string), " ", "_"))


def str_to_kebab(string):
    """Kebab case: lower case words separated by dashes."""

    check_character(string, "string")
    return copy_names(string, _replace_fixed(_to_words(string), " ", "-"))
