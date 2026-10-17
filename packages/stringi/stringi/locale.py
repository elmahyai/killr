"""Locale list, query, and the stringi default locale.

These follow stringi 1.8.9 on ICU. ``C`` and ``c``, including a dot suffix
such as ``C.UTF-8``, are ``en_US_POSIX``. An empty name, ``und``, and
``root`` select the current default. A missing character is
``stringi._na.NA``.
"""

from __future__ import annotations

import sys
import warnings

import icu

from stringi._na import NA

_NOT_GIVEN = object()


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _is_c_locale(text: str) -> bool:
    return bool(text) and text[0] in ("C", "c") and (len(text) == 1 or text[1] == ".")


def _default_name() -> str:
    name = icu.Locale.getDefault().getName()
    if _is_c_locale(name) or name in ("", "root", "und"):
        return "en_US_POSIX" if _is_c_locale(name) else "en_US"
    return name


def _as_one_string(value: object, allow_default: bool) -> str:
    if value is _NOT_GIVEN:
        raise ValueError("argument `locale` should not be a NULL")
    if value is None or value == "":
        if allow_default:
            return _default_name()
        if value is None:
            raise ValueError("argument `locale` should not be a NULL")
        raise ValueError("incorrect locale identifier")
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument `locale` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                "argument `locale` should be a single character string; "
                "only the first element is used"
            )
        value = value[0]
    if value is NA:
        raise ValueError("missing values in argument `locale` is not supported")
    if not isinstance(value, str):
        raise ValueError(
            "argument `locale` should be a character vector (or an object coercible to)"
        )
    if value == "":
        if allow_default:
            return _default_name()
        raise ValueError("incorrect locale identifier")
    canonical = icu.Locale.createCanonical(value).getName()
    if _is_c_locale(value) or _is_c_locale(canonical):
        return "en_US_POSIX"
    if canonical in ("", "root", "und"):
        if allow_default:
            return _default_name()
        raise ValueError("incorrect locale identifier")
    if canonical.startswith("@"):
        if not allow_default:
            raise ValueError("incorrect locale identifier")
        return _default_name() + canonical
    return canonical


def stri_locale_list():
    """List the locale identifiers ICU knows, in stringi sort order.

    The order is the English locale at primary strength with numeric
    collation, which is ``stri_sort(..., locale="en_US", numeric=TRUE,
    strength=1)``.
    """

    names = list(icu.Locale.getAvailableLocales())
    collator = icu.Collator.createInstance(icu.Locale("en_US"))
    collator.setStrength(icu.Collator.PRIMARY)
    collator.setAttribute(
        icu.UCollAttribute.NUMERIC_COLLATION, icu.UCollAttributeValue.ON
    )
    names.sort(key=collator.getSortKey)
    return names


def stri_locale_info(locale=None):
    """Return language, country, variant, and the canonical locale name.

    ``None`` or ``""`` selects the current default locale. The fields are
    strings. A component ICU leaves blank is an empty string.
    """

    prepared = _as_one_string(locale, allow_default=True)
    parsed = icu.Locale(prepared)
    name = icu.Locale.createCanonical(prepared).getName()
    if _is_c_locale(name):
        name = "en_US_POSIX"
        parsed = icu.Locale(name)
    return {
        "Language": parsed.getLanguage(),
        "Country": parsed.getCountry(),
        "Variant": parsed.getVariant(),
        "Name": name,
    }


def stri_locale_get():
    """Return the current default locale name."""

    return stri_locale_info(None)["Name"]


def stri_locale_set(locale):
    """Set the default locale and return the previous one.

    Prints the short ``stri_info`` line to stderr, the way R's ``message``
    does. An empty locale is an error. ``C`` becomes ``en_US_POSIX``.
    """

    previous = stri_locale_get()
    prepared = _as_one_string(locale, allow_default=False)
    icu.Locale.setDefault(icu.Locale(prepared))
    # Imported lazily: info.py calls back into this module.
    from stringi.info import stri_info

    print(f"You are now working with {stri_info(True)}", file=sys.stderr)
    return previous
