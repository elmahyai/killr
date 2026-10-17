"""Python translation of snakecase 0.11.1."""

from __future__ import annotations

import random
import re
import unicodedata
from typing import Iterable, Sequence


_DEFAULT_SEP = r"[^[:alnum:]]"
_CASES = (
    "snake", "small_camel", "big_camel", "screaming_snake", "parsed",
    "mixed", "lower_upper", "upper_lower", "swap", "all_caps",
    "lower_camel", "upper_camel", "internal_parsing", "none", "flip",
    "sentence", "random", "title",
)


def _is_alnum(c: str) -> bool:
    return c.isalnum()


def _replace_sep(s: str, sep_in: str | None) -> str:
    if sep_in is None:
        return s.replace("_", "_").replace(" ", "_")
    if sep_in == _DEFAULT_SEP:
        return re.sub(r"[^\w]", "_", s, flags=re.UNICODE)
    # R's POSIX classes occur in the documented custom patterns.
    sep_in = sep_in.replace(r"[:alnum:]", r"\w")
    return re.sub(sep_in, "_", s)


def _parse(s: str, option: int, numerals: str, sep_in: str | None) -> str:
    if abs(option) >= 4:
        raise ValueError("parsing_option must be between -4 and +4.")
    s = _replace_sep(s, sep_in)
    if numerals == "asis":
        s = re.sub(r"(?<=[^_0-9])([0-9])", r"_ \1", s)
        s = re.sub(r"([0-9])(?=[^_|0-9])", r"\1 _", s)
    if option in (1, -1):
        patterns = (
            (r"([A-Z][a-z]+)", r"_\1_"),
            (r"(\d+)", r"_\1_"),
            (r"([A-Z]{2,})", r"_\1_"),
            (r"((?<![A-Z])[A-Z](?![A-Za-z]))", r"_\1_"),
            (r"([^A-Za-z0-9])", r"_\1_"),
        )
    elif option in (2, -2):
        patterns = (
            (r"([A-Z]{2,})", r"_\1_"),
            (r"([A-Z][a-z]+)", r"_\1_"),
            (r"(\d+)", r"_\1_"),
            (r"((?<![A-Z])[A-Z](?![A-Za-z]))", r"_\1_"),
            (r"([^A-Za-z0-9])", r"_\1_"),
        )
    elif option in (3, -3):
        patterns = (
            (r"([A-Z]+[a-z]*)", r"_\1_"),
            (r"((?<![A-Za-z0-9])[a-z]+)", r"_\1_"),
            (r"(\d+)", r"_\1_"),
            (r"((?<![A-Z])[A-Z](?![A-Za-z]))", r"_\1_"),
            (r"([^A-Za-z0-9])", r"_\1_"),
        )
    else:
        patterns = ()
    for pattern, replacement in patterns:
        s = re.sub(pattern, replacement, s)
    s = re.sub(r"_+", "_", s).strip("_")
    if option in (-1, -2, -3):
        s = re.sub(r"_(?![A-Za-z0-9])|(?<![A-Za-z0-9])_", "", s)
    return s


def _transliterate(s: str, transliterations: Sequence[str] | None) -> str:
    if not transliterations:
        return s
    dictionaries = {
        "german": {"Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ä": "ae",
                   "ö": "oe", "ü": "ue", "ß": "ss"},
        "danish": {"Æ": "Ae", "æ": "ae", "Ø": "Oe", "ø": "oe",
                   "Å": "Aa", "å": "aa"},
        "finnish": {"Æ": "A", "æ": "a", "Ø": "O", "ø": "o"},
        "swedish": {"Æ": "A", "æ": "a", "Ø": "O", "ø": "o",
                    "Å": "A", "å": "a"},
    }
    for item in transliterations:
        if item in dictionaries:
            s = "".join(dictionaries[item].get(c, c) for c in s)
        elif item == "Latin-ASCII":
            s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        else:
            raise ValueError("Unsupported transliteration")
    return s


def _words(s: str, option: int, numerals: str, sep_in: str | None,
           transliterations: Sequence[str] | None, abbreviations: Sequence[str] | None):
    # Abbreviation markers are represented directly as boundaries. This covers
    # the public behavior while avoiding leakage of the internal marker text.
    if abbreviations:
        for abbr in sorted(set(abbreviations), key=len, reverse=True):
            s = re.sub(re.escape(abbr), "_" + abbr + "_", s, flags=re.IGNORECASE)
    parsed = _parse(s, option, numerals, sep_in)
    return [_transliterate(x, transliterations) for x in parsed.split("_")]


def _case_one(s: str, case: str, abbreviations, sep_in, parsing_option,
              transliterations, numerals) -> str:
    if s is None:
        return None
    if case in ("swap", "flip"):
        return "".join(c.lower() if c.isupper() else c.upper() if c.islower() else c
                       for c in s)
    if case == "random":
        return "".join(c.upper() if random.choice((True, False)) else c.lower()
                       for c in s)
    if case == "none":
        out = _replace_sep(s, sep_in)
        out = re.sub("_+", "_", out).strip("_")
        return _transliterate(out, transliterations)
    words = _words(s, parsing_option, numerals, sep_in, transliterations, abbreviations)
    if case == "internal_parsing":
        return "_" + "_".join(words) + "_"
    if case == "parsed":
        return "_".join(words)
    lower = [w.lower() for w in words]
    abbr_map = {a.lower(): a for a in abbreviations or ()}
    if case == "mixed":
        return "_".join(abbr_map.get(w.lower(), w[:1] + w[1:].lower()) for w in words)
    if case in ("snake", "screaming_snake"):
        out = "_".join(lower)
        return out.upper() if case == "screaming_snake" else out
    if case == "small_camel":
        parsed = _parse(s, parsing_option, numerals, sep_in)
        parts = re.split(r"(?<!\d)_|_(?!\d)", parsed)
        vals = [abbr_map.get(_transliterate(w, transliterations).lower(),
                             _transliterate(w, transliterations).lower())
                for w in parts]
        return (vals[0][:1].lower() + vals[0][1:] if vals else "") + "".join(
            v[:1].upper() + v[1:] for v in vals[1:])
    if case == "big_camel":
        parsed = _parse(s, parsing_option, numerals, sep_in)
        parts = re.split(r"(?<!\d)_|_(?!\d)", parsed)
        vals = [abbr_map.get(_transliterate(w, transliterations).lower(),
                             _transliterate(w, transliterations).lower())
                for w in parts]
        return "".join(v[:1].upper() + v[1:] for v in vals)
    if case in ("lower_upper", "upper_lower"):
        relevant = [bool(re.search(r"[A-Za-z]", w)) for w in words]
        flip = 0
        out = []
        for w, has_alpha in zip(words, relevant):
            if has_alpha:
                use_lower = (flip % 2 == 0)
                flip += 1
                out.append(w.lower() if (use_lower == (case == "lower_upper")) else w.upper())
            else:
                out.append(w)
        return "_".join(out)
    if case == "sentence":
        out = "_".join(lower)
        return out[:1].upper() + out[1:] if out else out
    raise ValueError(f"Unsupported case: {case}")


def to_any_case(string, case="snake", abbreviations=None, sep_in=_DEFAULT_SEP,
                parsing_option=1, transliterations=None, numerals="middle",
                sep_out=None, unique_sep=None, empty_fill=None, prefix="",
                postfix=""):
    title = case == "title"
    aliases = {"all_caps": "screaming_snake", "lower_camel": "small_camel",
               "upper_camel": "big_camel", "flip": "swap", "title": "sentence"}
    case = aliases.get(case, case)
    values = string if isinstance(string, (list, tuple)) else [string]
    result = [_case_one(x, case, abbreviations, sep_in, parsing_option,
                        transliterations, numerals) for x in values]
    if title:
        small = {"a", "an", "and", "as", "at", "but", "by", "for", "in",
                 "is", "of", "on", "or", "the", "this", "to"}
        result = [("_".join((w.lower() if i and (w.lower() in small or len(w) == 1)
                             else w[:1].upper() + w[1:])
                            for i, w in enumerate(x.split("_")))
                   if x is not None else None) for x in result]
    if sep_out is not None:
        outs = sep_out if isinstance(sep_out, (list, tuple)) else [sep_out]
        result = [re.sub("_", outs[min(i, len(outs)-1)], x) if x is not None else None
                  for i, x in enumerate(result)]
    elif case in ("small_camel", "big_camel", "lower_upper", "upper_lower"):
        result = [re.sub(r"(?<!\d)_|_(?!\d)", "", x) if x is not None else None for x in result]
    elif case == "sentence":
        result = [x.replace("_", " ") if x is not None else None for x in result]
    if empty_fill is not None:
        fill = empty_fill if isinstance(empty_fill, str) else empty_fill[0]
        result = [fill if x == "" else x for x in result]
    if unique_sep is not None:
        seen = {}
        for i, x in enumerate(result):
            n = seen.get(x, 0)
            result[i] = x if n == 0 else f"{x}{unique_sep}{n+1}"
            seen[x] = n + 1
    result = [None if x is None else prefix + x + postfix for x in result]
    return result if isinstance(string, (list, tuple)) else result[0]


def _shortcut(case):
    def f(string, abbreviations=None, sep_in=_DEFAULT_SEP, parsing_option=1,
          transliterations=None, numerals="middle", sep_out=None,
          unique_sep=None, empty_fill=None, prefix="", postfix=""):
        return to_any_case(string, case, abbreviations, sep_in, parsing_option,
                           transliterations, numerals, sep_out, unique_sep,
                           empty_fill, prefix, postfix)
    return f


to_snake_case = _shortcut("snake")
to_lower_camel_case = _shortcut("small_camel")
to_upper_camel_case = _shortcut("big_camel")
to_screaming_snake_case = _shortcut("screaming_snake")
to_parsed_case = _shortcut("parsed")
to_mixed_case = _shortcut("mixed")
to_lower_upper_case = _shortcut("lower_upper")
to_upper_lower_case = _shortcut("upper_lower")
to_swap_case = _shortcut("swap")
to_sentence_case = _shortcut("sentence")
to_random_case = _shortcut("random")
to_title_case = _shortcut("title")

