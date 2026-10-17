"""Character-vector summaries from stringi 1.8.9.

Whitespace is ICU's ``White_Space`` property. A newline inside a string
is an error. A missing string is skipped and is not a line.
"""

from __future__ import annotations

import icu

from stringi._na import NA
from stringi.join import _prepare_string

_WHITE = icu.UProperty.WHITE_SPACE


def _code_points(text: str):
    for char in text:
        yield ord(char)


def _reject_newline(code: int) -> None:
    if code in (0x0A, 0x0D):
        raise ValueError("newline character found in a string")


def stri_stats_general(str):
    """Count lines, non-empty lines, code points, and non-whitespace.

    A line is a non-missing string. It is non-empty when it contains a
    code point that is not ``White_Space``. ``CharsNWhite`` counts those
    code points.
    """

    strings = _prepare_string(str, "str")
    lines = 0
    nonempty = 0
    chars = 0
    nonwhite = 0
    for text in strings:
        if text is NA:
            continue
        lines += 1
        any_ink = False
        for code in _code_points(text):
            _reject_newline(code)
            chars += 1
            if not icu.Char.hasBinaryProperty(code, _WHITE):
                any_ink = True
                nonwhite += 1
        if any_ink:
            nonempty += 1
    return {
        "Lines": lines,
        "LinesNEmpty": nonempty,
        "Chars": chars,
        "CharsNWhite": nonwhite,
    }


def stri_stats_latex(str):
    """Count words, commands, and environments with the Kile word algorithm.

    A missing string is skipped. A newline inside a string is an error.
    ``%`` starts a comment that runs to the end of that string. ``\\begin``
    and ``\\end`` are environments; other letter commands are commands.
    """

    strings = _prepare_string(str, "str")
    chars_word = 0
    chars_cmd = 0
    chars_white = 0
    words = 0
    cmds = 0
    envirs = 0
    standard = 0
    comment = 1
    control = 3
    command = 5
    environment = 6
    for text in strings:
        if text is NA:
            continue
        state = standard
        in_word = False
        codes = list(text)
        index = 0
        size = len(codes)
        while index < size:
            char = codes[index]
            code = ord(char)
            index += 1
            _reject_newline(code)
            letter = icu.Char.isUAlphabetic(code)
            number = icu.Char.isdigit(code)
            if state == standard:
                if char == "\\":
                    state = control
                    chars_cmd += 1
                    if index < size:
                        nxt = ord(codes[index])
                        punct = icu.Char.ispunct(nxt)
                        if (not punct) or nxt in (ord("~"), ord("^")):
                            in_word = False
                elif char == "%":
                    state = comment
                elif letter or number:
                    if letter and not in_word:
                        in_word = True
                        words += 1
                    chars_word += 1
                else:
                    chars_white += 1
                    in_word = False
                continue
            if state == control:
                if letter:
                    rest = "".join(codes[index:])
                    if char == "b" and rest.startswith("egin"):
                        envirs += 1
                        state = environment
                        chars_cmd += 5
                        index += 4
                    elif char == "e" and rest.startswith("nd"):
                        chars_cmd += 3
                        state = environment
                        index += 2
                    else:
                        cmds += 1
                        chars_cmd += 1
                        state = command
                else:
                    cmds += 1
                    chars_cmd += 1
                    state = standard
                continue
            if state == command:
                if letter:
                    chars_cmd += 1
                elif char == "\\":
                    chars_cmd += 1
                    state = control
                elif char == "%":
                    state = comment
                else:
                    chars_white += 1
                    state = standard
                continue
            if state == environment:
                if char == "}":
                    chars_cmd += 1
                    state = standard
                elif char == "%":
                    state = comment
                else:
                    chars_cmd += 1
                continue
            if state == comment:
                continue
            raise ValueError("DEBUG: stri_stats_latex() - this shouldn't happen :-(")
    return {
        "CharsWord": chars_word,
        "CharsCmdEnvir": chars_cmd,
        "CharsWhite": chars_white,
        "Words": words,
        "Cmds": cmds,
        "Envirs": envirs,
    }
