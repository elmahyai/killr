"""Plain-scalar tags for libyaml's YAML 1.1 scanner.

PyYAML does not treat `y` and `n` as booleans, and it does treat `1:20` as an
integer. CRAN yaml does the opposite. Quoted text stays a string.
"""

import re

_YES = re.compile(r"^(?:y|Y|yes|Yes|YES|true|True|TRUE|on|On|ON)$")
_NO = re.compile(r"^(?:n|N|no|No|NO|false|False|FALSE|off|Off|OFF)$")
_NULL = re.compile(r"^(?:~|null|Null|NULL|)$")
_HEX = re.compile(r"^[-+]?0x[0-9a-fA-F]+$")
_OCT = re.compile(r"^[-+]?0[0-7]+$")
_INT = re.compile(r"^[-+]?(?:0|[1-9][0-9]*)$")
_BASE60 = re.compile(r"^[0-9]+:[0-5][0-9](?::[0-5][0-9])*$")
_FLOAT_BASE60 = re.compile(r"^[0-9]+:[0-5][0-9](?::[0-5][0-9])*\.[0-9]+$")
_FLOAT = re.compile(
    r"^(?:[-+]?(?:[0-9][0-9]*)?\.[0-9]*(?:[eE][-+][0-9]+)?|[-+]?[0-9]+[eE][-+][0-9]+)$"
)
_INF = re.compile(r"^[-+]?\.(?:inf|Inf|INF)$")
_NAN = re.compile(r"^\.(?:nan|NaN|NAN)$")
_YMD = re.compile(r"^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$")
_ISO = re.compile(
    r"^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
    r"[Tt][0-9][0-9]:[0-9][0-9]:[0-9][0-9](?:\.[0-9]+)?(?:Z|[-+][0-9][0-9]:[0-9][0-9])?$"
)


def implicit_tag(text):
    """Return the libyaml tag name for one plain scalar."""
    if text == ".na":
        return "bool#na"
    if text == ".na.real":
        return "float#na"
    if text == ".na.integer":
        return "int#na"
    if text == ".na.character":
        return "str#na"
    if text == "<<":
        return "merge"
    if _YES.match(text):
        return "bool#yes"
    if _NO.match(text):
        return "bool#no"
    if _NULL.match(text):
        return "null"
    if _NAN.match(text):
        return "float#nan"
    if _INF.match(text):
        return "float#neginf" if text[0] == "-" else "float#inf"
    if _HEX.match(text):
        return "int#hex"
    if _OCT.match(text):
        return "int#oct"
    if _INT.match(text):
        return "int"
    if _BASE60.match(text):
        return "int#base60"
    if _FLOAT_BASE60.match(text):
        return "float#base60"
    if _FLOAT.match(text):
        return "float#exp" if ("e" in text or "E" in text) else "float#fix"
    if _ISO.match(text):
        return "timestamp#iso8601"
    if _YMD.match(text):
        return "timestamp#ymd"
    return "str"


def tag_from_event(event):
    """Prefer an explicit tag. Otherwise classify a plain scalar."""
    explicit = event.tag
    plain = event.implicit[0]
    if explicit:
        if explicit.startswith("tag:yaml.org,2002:"):
            short = explicit[len("tag:yaml.org,2002:") :]
            if short == "bool":
                return implicit_tag(event.value) if implicit_tag(event.value).startswith("bool") else "bool"
            if short == "int" and plain:
                return implicit_tag(event.value)
            if short == "float" and plain:
                return implicit_tag(event.value)
            if short == "null":
                return "null"
            if short == "str":
                return "str"
            if short in ("seq", "map", "omap", "binary", "merge", "timestamp"):
                return short
            return short
        short = explicit
        while short.startswith("!"):
            short = short[1:]
        return short or "str"
    if plain:
        return implicit_tag(event.value)
    return "str"
