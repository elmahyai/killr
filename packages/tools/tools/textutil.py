"""Title case, non-ASCII lines, and URI references from tools 4.5.0."""

from __future__ import annotations

import re
import sys
from typing import Any

from tools.file_ext import NA, NA_character_, _is_alnum

_DELIMS = set(" -/\"()\n\t")
_LPAT = re.compile(
    r"^(a|an|and|are|as|at|be|but|by|en|for|if|in|is|nor|not|of|on|or|per|so|the|to|v[.]?|via|vs[.]?|from|into|than|that|with)$",
    re.IGNORECASE,
)
_ALONE = {
    "2D", "3D", "AIC", "BayesX", "GoF", "HTML", "LaTeX", "MonetDB", "OpenBUGS",
    "TeX", "U.S.", "U.S.A.", "WinBUGS", "aka", "et", "al.", "ggplot2", "i.e.",
    "jar", "jars", "ncdf", "netCDF", "rgl", "rpart", "xls", "xlsx",
    "all", "above", "after", "along", "also", "among", "any", "both", "can",
    "few", "it", "less", "log", "many", "may", "more", "over", "some", "their",
    "then", "this", "under", "until", "using", "von", "when", "where", "which",
    "will", "without", "yet", "you", "your",
}
_URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")


def _split(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for char in text:
        if char in _DELIMS:
            if buf:
                parts.append("".join(buf))
                buf = []
            parts.append(char)
        else:
            buf.append(char)
    if buf:
        parts.append("".join(buf))
    return parts


def _do1(word: str) -> str:
    if len(word) >= 3 and word[0] in "'\"":
        return word[0] + word[1].upper() + word[2:].lower()
    if not word:
        return word
    return word[0].upper() + word[1:].lower()


def _title_one(text: str | NA) -> str | NA:
    if isinstance(text, NA):
        return NA_character_
    words = _split(text)
    alone = [word in _ALONE or bool(re.match(r"^'.*'$", word)) for word in words]
    # A letter, then a later uppercase letter. That is R's [[:alpha:]].*[[:upper:]].
    havecaps = []
    for word in words:
        later = False
        if word and word[0].isalpha():
            later = any(char.isupper() for char in word[1:])
        havecaps.append(later)
    small = [bool(_LPAT.match(word)) for word in words]
    if small:
        small[0] = False
    ends = [index for index, word in enumerate(words) if word.endswith("-") or word.endswith(":")]
    for index in ends:
        follower = words[index + 2] if index + 2 < len(words) else ""
        starts = bool(follower) and (follower[0] == "'" or _is_alnum(follower[0]))
        if index + 2 < len(small) and words[index + 1] == " " and starts:
            if not (words[index] == "-" and _LPAT.match(words[index + 2])):
                small[index + 2] = False
    quotes = [index for index, word in enumerate(words) if word == '"']
    for index in quotes:
        if index + 1 < len(small):
            small[index + 1] = False
    for index, flag in enumerate(small):
        if flag:
            words[index] = words[index].lower()
    for index, word in enumerate(words):
        keep = havecaps[index] or small[index] or len(word) == 1 or alone[index]
        if not keep:
            words[index] = _do1(word)
    return "".join(words)


def to_title_case(text: Any) -> Any:
    """R's toTitleCase. Small words stay lower except after a break."""
    if isinstance(text, str) or isinstance(text, NA):
        text = [text]
    if text is None or any(not isinstance(item, (str, NA)) for item in text):
        raise ValueError("'text' must be a character vector")
    return [_title_one(item) for item in text]


def _ascii_bytes(text: str) -> str:
    pieces = []
    for byte in text.encode("utf-8"):
        if byte < 128:
            pieces.append(chr(byte))
        else:
            pieces.append(f"<{byte:02x}>")
    return "".join(pieces)


def show_non_ascii(x: Any) -> list[str]:
    """Print lines that are not ASCII, with non-ASCII bytes as <hex>, and return them."""
    if isinstance(x, str):
        x = [x]
    found = [index for index, line in enumerate(x) if isinstance(line, str) and any(ord(char) > 127 for char in line)]
    if found:
        print("\n".join(f"{index + 1}: {_ascii_bytes(x[index])}" for index in found), file=sys.stderr)
    return [x[index] for index in found]


def show_non_ascii_file(path: str) -> list[str]:
    """showNonASCII of the lines in a file. Warnings from readLines are dropped."""
    with open(path, encoding="utf-8", errors="surrogateescape") as handle:
        lines = handle.read().splitlines()
    return show_non_ascii(lines)


def parse_uri_reference(x: Any) -> list[dict[str, str]]:
    """Split URI references into scheme, authority, path, query, and fragment."""
    if x is None:
        return []
    if isinstance(x, str):
        x = [x]
    rows = []
    for item in x:
        match = _URI.match("" if item is None else item)
        groups = match.groups() if match else (None,) * 9
        def take(index: int) -> str:
            value = groups[index]
            return "" if value is None else value
        rows.append({
            "scheme": take(1),
            "authority": take(3),
            "path": take(4),
            "query": take(6),
            "fragment": take(8),
        })
    return rows
