"""Pseudo-random strings, shuffles, and lorem ipsum.

R and Python do not share a generator. These functions follow stringi's
shapes: Fisher-Yates over code points, uniform draws from an ICU
``UnicodeSet``, and the pure-R lorem ipsum in ``random.R``. A missing
character is ``stringi._na.NA``.
"""

from __future__ import annotations

import bisect
import math
import random
import warnings

import icu

from stringi._na import NA
from stringi.join import _prepare_integer, _prepare_string

_WORDS = (
    "SED", "IN", "UT", "ET", "AC", "EU", "NON", "NEC", "AMET", "SIT",
    "VEL", "AT", "MAURIS", "A", "VITAE", "EGET", "QUIS", "NUNC", "NULLA",
    "ID", "VESTIBULUM", "PELLENTESQUE", "TINCIDUNT", "ALIQUAM", "IPSUM",
    "DONEC", "TURPIS", "LIGULA", "EGESTAS", "NIBH", "SAPIEN", "ANTE", "NISL",
    "VELIT", "ERAT", "EROS", "LEO", "MAGNA", "JUSTO", "ENIM", "MI", "PURUS",
    "EST", "LACUS", "LOREM", "QUAM", "DIAM", "RISUS", "DOLOR", "SEM", "AUGUE",
    "NEQUE", "TEMPOR", "DUI", "ARCU", "METUS", "TORTOR", "URNA", "LIBERO",
    "PHARETRA", "TEMPUS", "FAUCIBUS", "LECTUS", "SUSPENDISSE", "FELIS", "ODIO",
    "ORCI", "VARIUS", "MASSA", "TELLUS", "VOLUTPAT", "BLANDIT", "INTERDUM",
    "LOBORTIS", "MAXIMUS", "NISI", "LUCTUS", "PORTTITOR", "AUCTOR", "ELEMENTUM",
    "EX", "MAECENAS", "MALESUADA", "TRISTIQUE", "ULLAMCORPER", "ULTRICES",
    "NULLAM", "CONSEQUAT", "LACINIA", "PHASELLUS", "ACCUMSAN", "DAPIBUS",
    "ELEIFEND", "COMMODO", "DUIS", "EFFICITUR", "ELIT", "IMPERDIET", "AENEAN",
    "IACULIS", "NAM", "CONSECTETUR", "FERMENTUM", "PORTA", "SCELERISQUE",
    "SODALES", "FEUGIAT", "LAOREET", "VULPUTATE", "DICTUM", "QUISQUE", "FACILISIS",
    "FINIBUS", "ORNARE", "PULVINAR", "RHONCUS", "CONDIMENTUM", "MOLLIS",
    "PRETIUM", "ALIQUET", "CONGUE", "POSUERE", "SUSCIPIT", "ULTRICIES", "CURABITUR",
    "GRAVIDA", "MATTIS", "VIVERRA", "CURSUS", "EUISMOD", "RUTRUM", "VENENATIS",
    "CONVALLIS", "PROIN", "VEHICULA", "PLACERAT", "SAGITTIS", "CRAS", "INTEGER",
    "MORBI", "VIVAMUS", "PRAESENT", "BIBENDUM", "MOLESTIE", "SEMPER", "FRINGILLA",
    "FUSCE", "DIGNISSIM", "ETIAM", "HENDRERIT", "SOLLICITUDIN", "PER", "FAMES",
    "POTENTI", "AD", "APTENT", "CLASS", "CONUBIA", "HIMENAEOS", "INCEPTOS",
    "LITORA", "NOSTRA", "SOCIOSQU", "TACITI", "TORQUENT", "HABITANT", "NETUS",
    "SENECTUS", "PRIMIS", "CUM", "DIS", "MAGNIS", "MONTES", "MUS", "NASCETUR",
    "NATOQUE", "PARTURIENT", "PENATIBUS", "RIDICULUS", "SOCIIS", "ADIPISCING",
    "FACILISI", "CUBILIA", "CURAE", "DICTUMST", "HABITASSE", "HAC", "PLATEA",
)

_NOT_GIVEN = object()


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _one_integer(value, name: str):
    values = _prepare_integer(value, name)
    if len(values) == 0:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if len(values) > 1:
        _warn(
            f"argument `{name}` should be a single integer value; "
            "only the first element is used"
        )
    if values[0] is NA:
        raise ValueError(f"missing values in argument `{name}` is not supported")
    return values[0]


def stri_rand_shuffle(str):
    """Permute the code points of each string.

    The permutation is Fisher-Yates. A missing string stays missing. The
    draw uses Python's random generator, not R's.
    """

    strings = _prepare_string(str, "str")
    result = []
    for text in strings:
        if text is NA:
            result.append(NA)
            continue
        codes = list(text)
        count = len(codes)
        for index in range(count - 1):
            choice = math.floor(random.random() * (count - index) + index)
            codes[choice], codes[index] = codes[index], codes[choice]
        result.append("".join(codes))
    return result


def _set_chars(pattern: str) -> list:
    try:
        charset = icu.UnicodeSet(pattern)
    except icu.ICUError as exc:
        raise ValueError(f"incorrect character class '{pattern}'") from exc
    if charset.isBogus():
        raise ValueError(f"incorrect character class '{pattern}'")
    chars = []
    for index in range(len(charset)):
        item = charset[index]
        chars.append(item if isinstance(item, str) else chr(item))
    if not chars:
        raise ValueError(f"incorrect character class '{pattern}'")
    return chars


def stri_rand_strings(n, length, pattern="[A-Za-z0-9]"):
    """Draw strings of the requested lengths from a character class.

    Sampling is with replacement and each code point is equally likely.
    A negative length yields an empty string. A missing length or pattern
    yields a missing string. ``n < 0`` yields an empty vector.
    """

    count = _one_integer(n, "n")
    if count < 0:
        count = 0
    lengths = _prepare_integer(length, "length")
    patterns = _prepare_string(pattern, "pattern")
    if len(lengths) == 0:
        raise ValueError("argument `length` should be a non-empty vector")
    if len(patterns) == 0:
        raise ValueError("argument `pattern` should be a non-empty vector")
    if count == 0:
        return []
    if len(lengths) > count or count % len(lengths) != 0:
        _warn("vector length not consistent with other arguments")
    if len(patterns) > count or count % len(patterns) != 0:
        _warn("vector length not consistent with other arguments")
    alphabets = []
    for item in patterns:
        if item is NA:
            alphabets.append(None)
        else:
            alphabets.append(_set_chars(item))
    result = []
    for index in range(count):
        size = lengths[index % len(lengths)]
        alphabet = alphabets[index % len(alphabets)]
        if size is NA or alphabet is None:
            result.append(NA)
            continue
        if size < 0:
            size = 0
        width = len(alphabet)
        chars = []
        for _ in range(size):
            pick = math.floor(random.random() * width)
            chars.append(alphabet[pick])
        result.append("".join(chars))
    return result


def _rwords(count: int) -> list:
    total = len(_WORDS)
    weights = [1.0 / (k ** 0.5) for k in range(1, total + 1)]
    scale = sum(weights)
    cumulative = [0.0]
    running = 0.0
    for weight in weights:
        running += weight / scale
        cumulative.append(running)
    chosen = []
    for _ in range(count):
        slot = bisect.bisect_right(cumulative, random.random()) - 1
        if slot < 0:
            slot = 0
        if slot >= total:
            slot = total - 1
        chosen.append(_WORDS[slot])
    return chosen


def _rtruncnorm(count, low, high, mu, sd):
    def draw():
        return round(random.gauss(mu, sd))

    values = [draw() for _ in range(count)]
    while any(item < low or item > high for item in values):
        for index, item in enumerate(values):
            if item < low or item > high:
                values[index] = draw()
    return values


def _title_sentence(text: str) -> str:
    holder = icu.UnicodeString(text)
    locale = icu.Locale.getDefault()
    breaker = icu.BreakIterator.createSentenceInstance(locale)
    return str(holder.toTitle(breaker, locale))


def stri_rand_lipsum(n_paragraphs=_NOT_GIVEN, start_lipsum=True, nparagraphs=_NOT_GIVEN):
    """Generate lorem ipsum paragraphs.

    Word counts follow the Zipf weights in stringi's R source, and sentence
    and paragraph lengths follow a truncated discrete normal. The generator
    is Python's, so the paragraphs are not the same draws as R. Each
    paragraph is title-cased on sentence boundaries. ``start_lipsum`` is
    honored only when it is exactly ``True``.
    """

    if nparagraphs is not _NOT_GIVEN and n_paragraphs is _NOT_GIVEN:
        warnings.warn(
            "The 'nparagraphs' argument in stri_rand_lipsum is a deprecated "
            "alias of 'n_paragraphs' and will be removed in a future release "
            "of 'stringi'.",
            UserWarning,
            stacklevel=2,
        )
        n_paragraphs = nparagraphs
    if n_paragraphs is _NOT_GIVEN:
        raise TypeError("stri_rand_lipsum() missing argument 'n_paragraphs'")
    count = _one_integer(n_paragraphs, "n_paragraphs")
    if count < 1:
        raise ValueError("is.finite(n_paragraphs), n_paragraphs >= 1 are not all TRUE")
    opening = start_lipsum is True
    sentences = _rtruncnorm(count, 7, 20, 11, 3)
    words_per = [_rtruncnorm(item, 2, math.inf, 8, 3) for item in sentences]
    total_words = sum(sum(group) for group in words_per)
    words = _rwords(total_words)
    separators = random.choices([" ", ", "], weights=[0.9, 0.1], k=total_words)
    sentence_ends = []
    cursor = 0
    for group in words_per:
        for size in group:
            cursor += size
            sentence_ends.append(cursor - 1)
    endings = random.choices(
        [". ", "? ", "! "], weights=[0.95, 0.025, 0.025], k=len(sentence_ends)
    )
    for index, ending in zip(sentence_ends, endings):
        separators[index] = ending
    paragraph_at = []
    cursor = 0
    for group in words_per:
        cursor += sum(group)
        paragraph_at.append(cursor - 1)
    for index in paragraph_at:
        separators[index] = ".\n"
    separators[total_words - 1] = "."
    if opening:
        words = ["LOREM", "IPSUM", "DOLOR", "SIT", "AMET", *words]
        separators = [" ", " ", " ", " ", ", ", *separators]
    pasted = "".join(word + sep for word, sep in zip(words, separators))
    paragraphs = pasted.split("\n")
    return [_title_sentence(part) for part in paragraphs]
