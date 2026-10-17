"""Case mapping, character translation, and ICU transliteration.

These follow stringi 1.8.9 on ICU 76. Case mapping is locale-sensitive and
context-sensitive, so it goes through PyICU. Python ``str.lower`` and
``unicodedata`` are a different Unicode version and do not implement
Turkish ``i``/``I`` or Lithuanian ``I`` plus a combining dot.

A missing character is ``stringi._na.NA``. The string ``"NA"`` is text.
"""

from __future__ import annotations

import functools
import warnings

import icu

from stringi._na import NA, is_na
from stringi.length import _prepare
from stringi.opts import stri_opts_brkiter

_BREAKS = ("character", "line_break", "sentence", "word")
_SIDE_NOTE = "incorrect break iterator option specifier, see ?stri_opts_brkiter"


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=2)


def _finish(result: list, scalar: bool):
    if scalar and len(result) == 1:
        return result[0]
    return result


def _one_string(value, name: str):
    texts, _scalar = _prepare(value)
    if not texts:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if len(texts) > 1:
        _warn(
            f"argument `{name}` should be a single character string; "
            "only the first element is used"
        )
    return texts[0]


def _logical_1(value, name: str) -> bool:
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                f"argument `{name}` should be a single logical value; "
                "only the first element is used"
            )
        value = value[0]
    if is_na(value):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    raise TypeError(f"argument `{name}` should be a single logical value")


def _c_locale(name: str) -> bool:
    return bool(name) and name[0] in "Cc" and (len(name) == 1 or name[1] == ".")


def _open_locale(value):
    """ICU locale. ``None`` and ``""`` select the default locale."""

    if value is None:
        return icu.Locale.getDefault()
    chosen = _one_string(value, "locale")
    if is_na(chosen):
        raise ValueError("missing values in argument `locale` is not supported")
    if chosen == "":
        return icu.Locale.getDefault()
    if _c_locale(chosen):
        return icu.Locale("en_US_POSIX")
    trimmed = chosen.strip(" \t\r\n")
    if trimmed == "":
        return icu.Locale.getDefault()
    if _c_locale(trimmed):
        return icu.Locale("en_US_POSIX")
    return icu.Locale(trimmed)


def _lower(text: str, locale) -> str:
    converted = icu.UnicodeString(text)
    converted.toLower(locale)
    return str(converted)


def _upper(text: str, locale) -> str:
    converted = icu.UnicodeString(text)
    converted.toUpper(locale)
    return str(converted)


def _title(text: str, breaker, locale) -> str:
    converted = icu.UnicodeString(text)
    converted.toTitle(breaker, locale)
    return str(converted)


def _fold(text: str) -> str:
    return icu.CaseMap.fold(icu.U_FOLD_CASE_DEFAULT, text)


def _map_case(value, func):
    texts, scalar = _prepare(value)
    if not texts:
        return []
    result = []
    for text in texts:
        if is_na(text):
            result.append(NA)
        else:
            result.append(func(text))
    return _finish(result, scalar)


def stri_trans_tolower(str, locale=None):
    """Map each string to lower case with ICU.

    ``locale`` ``None`` or ``""`` uses the default locale. ``"tr"`` and
    ``"tr_TR"`` map ``I`` to dotless ``ı``. A missing string stays missing.
    """

    loc = _open_locale(locale)
    return _map_case(str, lambda text: _lower(text, loc))


def stri_trans_toupper(str, locale=None):
    """Map each string to upper case with ICU.

    ``locale`` ``None`` or ``""`` uses the default locale. ``"tr"`` and
    ``"tr_TR"`` map ``i`` to dotted ``İ``. German ``ß`` expands to ``SS``.
    A missing string stays missing.
    """

    loc = _open_locale(locale)
    return _map_case(str, lambda text: _upper(text, loc))


def stri_trans_casefold(str):
    """Fold case with ICU's default full case folding.

    This is locale-independent. It is not ``str.casefold`` and it is not
    NFKC_Casefold. Dotted capital ``İ`` folds to ``i`` plus a combining
    dot. A missing string stays missing.
    """

    return _map_case(str, _fold)


def _match_break(option: str) -> str | None:
    if option in _BREAKS:
        return option
    hits = [name for name in _BREAKS if name.startswith(option)]
    if len(hits) == 1:
        return hits[0]
    return None


def _break_type(value) -> str:
    if value is None:
        return "word"
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument `type` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                "argument `type` should be a single character string; "
                "only the first element is used"
            )
        value = value[0]
    if is_na(value):
        raise ValueError("incorrect option for `type`")
    if not isinstance(value, str):
        value = _one_string(value, "type")
        if is_na(value):
            raise ValueError("incorrect option for `type`")
    matched = _match_break(value)
    if matched is None:
        return value
    return matched


def _breaker(kind: str, locale):
    if kind == "character":
        return icu.BreakIterator.createCharacterInstance(locale)
    if kind == "line_break":
        return icu.BreakIterator.createLineInstance(locale)
    if kind == "sentence":
        return icu.BreakIterator.createSentenceInstance(locale)
    if kind == "word":
        return icu.BreakIterator.createWordInstance(locale)
    try:
        return icu.RuleBasedBreakIterator(kind)
    except icu.ICUError as exc:
        raise ValueError(str(exc)) from exc


def _title_options(opts_brkiter, kwargs) -> dict:
    if kwargs:
        if opts_brkiter is None:
            base: dict = {}
        elif isinstance(opts_brkiter, dict):
            overlap = [name for name in opts_brkiter if name in kwargs]
            if overlap:
                raise TypeError(
                    f'formal argument "{overlap[0]}" matched by multiple actual arguments'
                )
            base = dict(opts_brkiter)
        else:
            raise ValueError(_SIDE_NOTE)
        return stri_opts_brkiter(**base, **kwargs)
    if opts_brkiter is None:
        return {}
    if isinstance(opts_brkiter, dict):
        return opts_brkiter
    raise ValueError(_SIDE_NOTE)


def stri_trans_totitle(str, opts_brkiter=None, **kwargs):
    """Map each string to title case with an ICU break iterator.

    The default iterator is ``word``: the first letter of each word is
    upper case and the rest is lower case. ``type="sentence"`` titles
    the first letter of each sentence. ``locale`` is read from the break
    iterator options. A missing string stays missing.
    """

    opts = _title_options(opts_brkiter, kwargs)
    locale = _open_locale(opts.get("locale"))
    breaker = _breaker(_break_type(opts.get("type")), locale)
    return _map_case(str, lambda text: _title(text, breaker, locale))


def _icu_call(func):
    try:
        return func()
    except icu.ICUError as exc:
        text = str(exc)
        if "unknown transliterator" in text:
            raise ValueError(
                "A '::id' rule specifies an unknown transliterator. (U_INVALID_ID)"
            ) from exc
        raise ValueError(text) from exc


def stri_trans_general(str, id, rules=False, forward=True):
    """Transliterate each string with an ICU transform id or rule set.

    ``rules`` false treats ``id`` as a transform identifier such as
    ``Latin-ASCII`` or ``Any-Hex``. ``rules`` true compiles ``id`` as
    transliterator rules. ``forward`` false runs the inverse transform.
    A missing ``id`` makes every result missing. A missing string stays
    missing.
    """

    texts, scalar = _prepare(str)
    ident = _one_string(id, "id")
    use_rules = _logical_1(rules, "rules")
    go_forward = _logical_1(forward, "forward")
    if not texts:
        return []
    if is_na(ident):
        return _finish([NA] * len(texts), scalar)
    direction = (
        icu.UTransDirection.FORWARD if go_forward else icu.UTransDirection.REVERSE
    )
    if use_rules:
        transformer = _icu_call(
            lambda: icu.Transliterator.createFromRules(
                "Rule-based Transliterator", ident, direction
            )
        )
    else:
        transformer = _icu_call(
            lambda: icu.Transliterator.createInstance(ident, direction)
        )
    result = []
    for text in texts:
        if is_na(text):
            result.append(NA)
        else:
            result.append(transformer.transliterate(text))
    return _finish(result, scalar)


def stri_trans_list():
    """Return every ICU transliterator id, sorted as stringi sorts them.

    The order is a stable sort with locale ``en_US``, primary strength,
    and numeric collation. That is ``stri_sort(locale="en_US", numeric=TRUE,
    strength=1)`` applied to ``Transliterator.getAvailableIDs``.
    """

    names = list(icu.Transliterator.getAvailableIDs())
    collator = icu.Collator.createInstance(icu.Locale("en_US"))
    collator.setStrength(icu.Collator.PRIMARY)
    collator.setAttribute(
        icu.UCollAttribute.NUMERIC_COLLATION, icu.UCollAttributeValue.ON
    )

    def order(left: str, right: str) -> int:
        return collator.compare(left, right)

    return sorted(names, key=functools.cmp_to_key(order))


def stri_trans_char(str, pattern, replacement):
    """Replace code points in each string using a character-to-character map.

    Only the shared prefix of ``pattern`` and ``replacement`` is used.
    A longer argument warns ``vector length not consistent with other
    arguments`` and its extra code points are ignored. When a pattern
    code point is repeated, the last paired replacement is kept. A missing
    pattern or replacement makes every result missing. A missing string
    stays missing. The string ``"NA"`` is text.
    """

    texts, scalar = _prepare(str)
    pat = _one_string(pattern, "pattern")
    rep = _one_string(replacement, "replacement")
    if is_na(pat) or is_na(rep):
        return _finish([NA] * len(texts), scalar)
    if len(pat) != len(rep):
        _warn("vector length not consistent with other arguments")
    mapping: dict[str, str] = {}
    for source, dest in zip(pat, rep):
        mapping[source] = dest
    result = []
    for text in texts:
        if is_na(text):
            result.append(NA)
        elif not mapping:
            result.append(text)
        else:
            result.append("".join(mapping.get(char, char) for char in text))
    return _finish(result, scalar)
