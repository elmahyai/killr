"""Color R source with the built-in syntax themes."""

from __future__ import annotations

import re
from pathlib import Path

from cli.styles import combine_ansi_styles, make_ansi_style, style_bold

_RESERVED = {
    "if", "else", "repeat", "while", "function", "for", "in", "next", "break",
    "NULL", "NA", "NA_integer_", "NA_real_", "NA_character_", "NA_complex_",
    "Inf", "NaN", "TRUE", "FALSE", "NA_integer_",
}
_THEMES = None


def _load_themes() -> dict:
    global _THEMES
    if _THEMES is not None:
        return _THEMES
    themes: dict[str, dict] = {}
    path = Path(__file__).parent / "data" / "code_theme_colors.tsv"
    for line in path.read_text(encoding="utf-8").splitlines():
        name, key, *values = line.split("\t")
        themes.setdefault(name, {})[key] = values
    _THEMES = themes
    return themes


def code_theme_list() -> list[str]:
    path = Path(__file__).parent / "data" / "code_themes.txt"
    return path.read_text(encoding="utf-8").splitlines()


def _painter(specs: list[str]):
    styles = []
    for spec in specs:
        if spec == "bold":
            styles.append(style_bold)
        elif spec == "italic":
            from cli.styles import style_italic

            styles.append(style_italic)
        elif spec.startswith("#") or spec.isalpha():
            styles.append(make_ansi_style(spec))
    if not styles:
        return lambda text: text
    if len(styles) == 1:
        return styles[0]
    return combine_ansi_styles(*styles)


def _theme_painters(name: str | None):
    themes = _load_themes()
    chosen_name = name or "Solarized Dark"
    if chosen_name not in themes:
        folded = {key.lower().replace(" ", "_"): key for key in themes}
        chosen_name = folded.get(chosen_name.lower().replace(" ", "_"), "Solarized Dark")
    chosen = themes[chosen_name]
    painters = {key: _painter(values) for key, values in chosen.items() if key != "bracket"}
    brackets = [_painter([value]) for value in chosen.get("bracket", [])]
    return painters, brackets


_TOKEN = re.compile(
    r"""
    (\#.*)
    |("[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')
    |(<<-|->>|<-|->|<=|>=|==|!=|&&|\|\||:::|::|%/%|%%|%in%|\*\*|\^|=|[+\-*/!~?:$@&|])
    |(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
    |([A-Za-z.][A-Za-z0-9._]*)
    |([(){}\[\]])
    |(\s+)
    |(.)
    """,
    re.VERBOSE,
)


def _color_brackets(chars: list[str], painters) -> list[str]:
    if not painters:
        return chars
    level = 0
    opens = {"(", "{", "[", "[["}
    out = []
    stack = []
    index = 0
    while index < len(chars):
        token = chars[index]
        if token in opens:
            level += 1
            stack.append(token)
            paint = painters[(level - 1) % len(painters)]
            out.append(paint(token))
            index += 1
            continue
        if stack:
            paint = painters[(level - 1) % len(painters)]
            width = len(stack[-1])
            out.extend(paint(part) for part in chars[index : index + width])
            index += width
            level -= 1
            stack.pop()
            continue
        out.append(token)
        index += 1
    return out


def code_highlight(code, code_theme=None, envir=None):
    """Color one R expression with a built-in theme. Invalid code is returned unchanged."""

    if isinstance(code, (list, tuple)):
        return [code_highlight(line, code_theme=code_theme, envir=envir) for line in code]
    text = "" if code is None else str(code)
    painters, brackets = _theme_painters(code_theme)
    pieces = []
    bracket_at = []
    for match in _TOKEN.finditer(text):
        comment, string, operator, number, name, bracket, space, other = match.groups()
        raw = match.group(0)
        if comment and painters.get("comment"):
            pieces.append(painters["comment"](raw))
        elif string and painters.get("string"):
            pieces.append(painters["string"](raw))
        elif operator and painters.get("operator"):
            pieces.append(painters["operator"](raw))
        elif number and painters.get("number"):
            pieces.append(painters["number"](raw))
        elif name == "NULL" and painters.get("null"):
            pieces.append(painters["null"](raw))
        elif name in _RESERVED and painters.get("reserved"):
            pieces.append(painters["reserved"](raw))
        elif bracket:
            bracket_at.append(len(pieces))
            pieces.append(raw)
        else:
            pieces.append(raw)
    if brackets and bracket_at:
        colored = _color_brackets([pieces[i] for i in bracket_at], brackets)
        for index, value in zip(bracket_at, colored):
            pieces[index] = value
    return "".join(pieces)


def pretty_print_code():
    from cli.messages import cli_alert_success

    cli_alert_success("Registered pretty printing function method")
    return None
