"""``utils::type.convert`` for character vectors, as R 4.5 implements it.

``colsplit`` calls it with ``as.is = TRUE``. A blank field is missing when the
column becomes logical, integer, or double, and the string ``"NA"`` is missing
in every type. A column that stays character keeps an empty string.
"""

from __future__ import annotations

import re
from typing import Any

from reshape2.frame import Column, is_na


_SPACE = " \t\n\r\v\f"
_REAL_RE = re.compile(
    r"[+-]?(?:"
    r"inf(?:inity)?"
    r"|nan"
    r"|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    r"|0[xX](?:[0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?|\.[0-9a-fA-F]+)(?:[pP][+-]?\d+)?"
    r")",
    re.IGNORECASE,
)
_INT_RE = re.compile(r"[+-]?\d+")


def _as_text(value: Any) -> str | None:
    if is_na(value):
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _blank(text: str) -> bool:
    return text.strip(_SPACE) == ""


def _missing_token(text: str | None, na_strings: tuple[str, ...]) -> bool:
    if text is None:
        return True
    if text in na_strings or _blank(text):
        return True
    return False


def _parse_int(text: str) -> int | None:
    index = 0
    while index < len(text) and text[index] in _SPACE:
        index += 1
    body = text[index:]
    if _INT_RE.fullmatch(body) is None:
        return None
    value = int(body, 10)
    if value < -2147483647 or value > 2147483647:
        return None
    return value


def _parse_real(text: str, strict: bool) -> float | None:
    body = text.strip(_SPACE)
    if not body or "_" in body:
        return None
    # Screening rejects an NA prefix, including ``NAN``. The conversion
    # itself still accepts a nan token, which is what ``strtod`` does.
    if body.startswith("NA"):
        if strict or body.lower() != "nan":
            return None
        return float("nan")
    if _REAL_RE.fullmatch(body) is None:
        return None
    if body.lower().lstrip("+-").startswith("0x"):
        try:
            return float.fromhex(body)
        except ValueError:
            return None
    try:
        return float(body)
    except ValueError:
        return None


def _parse_complex(text: str, strict: bool) -> tuple[float, float] | None:
    body = text.strip(_SPACE)
    if not body:
        return None
    if not body.endswith("i"):
        real = _parse_real(body, strict)
        if real is None:
            return None
        return (real, 0.0)
    core = body[:-1]
    if not core or core in ("+", "-"):
        return None
    split = None
    for index, char in enumerate(core):
        if char in "+-" and index > 0 and core[index - 1] not in "eEpP":
            split = index
    if split is None:
        imag = _parse_real(core, strict)
        if imag is None:
            return None
        return (0.0, imag)
    real = _parse_real(core[:split], strict)
    imag = _parse_real(core[split:], strict)
    if real is None or imag is None:
        return None
    return (real, imag)


def _ruleout(text: str, info: dict[str, bool]) -> None:
    if info["logical"]:
        if text in ("F", "T", "FALSE", "TRUE"):
            info["integer"] = False
            info["real"] = False
            info["complex"] = False
            return
        info["logical"] = False
    if info["integer"] and _parse_int(text) is None:
        info["integer"] = False
    if info["real"] and _parse_real(text, True) is None:
        info["real"] = False
    if info["complex"] and _parse_complex(text, True) is None:
        info["complex"] = False


def _character_column(strings: list[str | None], na_strings: tuple[str, ...]) -> Column:
    values: list[Any] = []
    for text in strings:
        if text is not None and text in na_strings:
            values.append(None)
        else:
            values.append(text)
    return Column("character", values)


def type_convert(
    values: Any,
    na_strings: tuple[str, ...] | list[str] = ("NA",),
    as_is: bool = True,
) -> Column:
    """Convert one character column the way ``type.convert(..., as.is=)`` does."""

    if isinstance(na_strings, list):
        na_strings = tuple(na_strings)
    strings = [_as_text(value) for value in values]
    info = {"logical": True, "integer": True, "real": True, "complex": True}
    for text in strings:
        if not _missing_token(text, na_strings):
            _ruleout(text, info)
            break

    def missing(text: str | None) -> bool:
        return _missing_token(text, na_strings)

    if info["logical"]:
        out: list[Any] = []
        ok = True
        for text in strings:
            if missing(text):
                out.append(None)
            elif text in ("T", "TRUE"):
                out.append(True)
            elif text in ("F", "FALSE"):
                out.append(False)
            else:
                info["logical"] = False
                _ruleout(text, info)
                ok = False
                break
        if ok:
            return Column("logical", out)

    if info["integer"]:
        out = []
        ok = True
        for text in strings:
            if missing(text):
                out.append(None)
            else:
                parsed = _parse_int(text)
                if parsed is None:
                    info["integer"] = False
                    _ruleout(text, info)
                    ok = False
                    break
                out.append(parsed)
        if ok:
            return Column("integer", out)

    if info["real"]:
        out = []
        ok = True
        for text in strings:
            if missing(text):
                out.append(None)
            else:
                parsed = _parse_real(text, False)
                if parsed is None:
                    info["real"] = False
                    _ruleout(text, info)
                    ok = False
                    break
                out.append(parsed)
        if ok:
            return Column("double", out)

    if info["complex"]:
        out = []
        ok = True
        for text in strings:
            if missing(text):
                out.append(None)
            else:
                parsed = _parse_complex(text, False)
                if parsed is None:
                    info["complex"] = False
                    _ruleout(text, info)
                    ok = False
                    break
                out.append(complex(parsed[0], parsed[1]))
        if ok:
            return Column("complex", out)

    if as_is:
        return _character_column(strings, na_strings)

    kept = _character_column(strings, na_strings)
    levels: list[str] = []
    seen: set[str] = set()
    for value in kept.values:
        if value is None or value in seen:
            continue
        seen.add(value)
        levels.append(value)
    levels.sort()
    index = {level: code for code, level in enumerate(levels, start=1)}
    codes = [None if value is None else index[value] for value in kept.values]
    return Column("integer", codes, {"levels": levels, "class": "factor"})
