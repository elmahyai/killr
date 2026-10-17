"""First and all matches through Python's re module.

rematch2 defaults to perl=TRUE. Python's re is the standard library, so it
is not a new native dependency. R's POSIX classes such as [[:upper:]] are
rewritten to ASCII ranges: this PCRE build treats those classes as ASCII.
"""

import re

_POSIX = {
    "alnum": "0-9A-Za-z",
    "alpha": "A-Za-z",
    "blank": " \\t",
    "cntrl": "\\x00-\\x1F\\x7F",
    "digit": "0-9",
    "graph": "!-~",
    "lower": "a-z",
    "print": " -~",
    "punct": r"!-/:-@\[-`{-~",
    "space": " \\t\\n\\r\\f\\v",
    "upper": "A-Z",
    "xdigit": "0-9A-Fa-f",
    "word": "0-9A-Za-z_",
}


def as_text(text):
    """One string is one element. None inside the vector is R's NA."""
    if isinstance(text, str):
        return [text]
    if text is None:
        return []
    return list(text)


def check_pattern(pattern):
    if not isinstance(pattern, str):
        raise ValueError("pattern must be one character string")


def _posix_classes(pattern):
    """Replace [:name:] so [[:upper:]] becomes [A-Z]."""

    def replace(match):
        name = match.group(1)
        if name not in _POSIX:
            raise ValueError(f"unknown POSIX class [:{name}:]")
        return _POSIX[name]

    return re.sub(r"\[:([a-z]+):\]", replace, pattern)


def _pcre_names(pattern):
    """Python's re accepts (?P<name>...), not PCRE's (?<name>...).

    Lookbehind (?<=...) and (?<!...) are left as they are.
    """
    return re.sub(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>", r"(?P<\1>", pattern)


def compile_pattern(pattern, perl=True, ignore_case=False, fixed=False):
    check_pattern(pattern)
    if fixed:
        source = re.escape(pattern)
    else:
        source = _posix_classes(pattern)
        if perl:
            source = _pcre_names(source)
    flags = re.IGNORECASE if ignore_case else 0
    compiled = re.compile(source, flags)
    if perl and not fixed:
        names = capture_names(compiled)
    else:
        names = []
    return compiled, names


def capture_names(compiled):
    by_index = {index: name for name, index in compiled.groupindex.items()}
    return [by_index.get(index, "") for index in range(1, compiled.groups + 1)]


def _piece(text, match, group):
    """One capture. A missed group is an empty string at position 0.

    A failed match is NA. Python reports a missed group as None and span
    (-1, -1); R's PCRE reports start 0 and length 0.
    """
    if match is None:
        return None, None, None
    if group != 0 and match.group(group) is None:
        return "", 0, -1
    start, end = match.span(group)
    return text[start:end], start + 1, end


def first_match(text, compiled):
    if text is None:
        return None
    return compiled.search(text)


def all_matches(text, compiled):
    if text is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    return list(compiled.finditer(text))


def match_string(text, match, group):
    value, _start, _end = _piece(text, match, group)
    return value


def match_record(text, match, group):
    value, start, end = _piece(text, match, group)
    return {"match": value, "start": start, "end": end}


def all_strings(text, matches, group):
    return [match_string(text, match, group) for match in matches]


def all_record(text, matches, group):
    rows = [match_record(text, match, group) for match in matches]
    return {
        "match": [row["match"] for row in rows],
        "start": [row["start"] for row in rows],
        "end": [row["end"] for row in rows],
    }
