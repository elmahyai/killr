"""cli symbols. Unicode when is_utf8_output() is true, otherwise ASCII."""

from __future__ import annotations

import unicodedata

from cli.unicode_output import is_utf8_output

SYMBOL_UTF8 = {
    'tick': '✔',
    'cross': '✖',
    'star': '★',
    'square': '▇',
    'square_small': '◻',
    'square_small_filled': '◼',
    'circle': '◯',
    'circle_filled': '◉',
    'circle_dotted': '◌',
    'circle_double': '◎',
    'circle_circle': 'ⓞ',
    'circle_cross': 'ⓧ',
    'circle_pipe': 'Ⓘ',
    'circle_question_mark': '?⃝',
    'bullet': '•',
    'dot': '․',
    'line': '─',
    'double_line': '═',
    'ellipsis': '…',
    'continue': '…',
    'pointer': '❯',
    'info': 'ℹ',
    'warning': '⚠',
    'menu': '☰',
    'smiley': '☺',
    'mustache': '෴',
    'heart': '♥',
    'arrow_up': '↑',
    'arrow_down': '↓',
    'arrow_left': '←',
    'arrow_right': '→',
    'radio_on': '◉',
    'radio_off': '◯',
    'checkbox_on': '☒',
    'checkbox_off': '☐',
    'checkbox_circle_on': 'ⓧ',
    'checkbox_circle_off': 'Ⓘ',
    'fancy_question_mark': '❓',
    'neq': '≠',
    'geq': '≥',
    'leq': '≤',
    'times': '×',
    'upper_block_1': '▔',
    'upper_block_4': '▀',
    'lower_block_1': '▁',
    'lower_block_2': '▂',
    'lower_block_3': '▃',
    'lower_block_4': '▄',
    'lower_block_5': '▅',
    'lower_block_6': '▆',
    'lower_block_7': '▇',
    'lower_block_8': '█',
    'full_block': '█',
    'sup_0': '⁰',
    'sup_1': '¹',
    'sup_2': '²',
    'sup_3': '³',
    'sup_4': '⁴',
    'sup_5': '⁵',
    'sup_6': '⁶',
    'sup_7': '⁷',
    'sup_8': '⁸',
    'sup_9': '⁹',
    'sup_minus': '⁻',
    'sup_plus': '⁺',
    'play': '▶',
    'stop': '■',
    'record': '●',
    'figure_dash': '‒',
    'en_dash': '–',
    'em_dash': '—',
    'dquote_left': '“',
    'dquote_right': '”',
    'squote_left': '‘',
    'squote_right': '’',
}

SYMBOL_ASCII = {
    'tick': 'v',
    'cross': 'x',
    'star': '*',
    'square': '[ ]',
    'square_small': '[ ]',
    'square_small_filled': '[x]',
    'circle': '( )',
    'circle_filled': '(*)',
    'circle_dotted': '( )',
    'circle_double': '(o)',
    'circle_circle': '(o)',
    'circle_cross': '(x)',
    'circle_pipe': '(|)',
    'circle_question_mark': '(?)',
    'bullet': '*',
    'dot': '.',
    'line': '-',
    'double_line': '=',
    'ellipsis': '...',
    'continue': '~',
    'pointer': '>',
    'info': 'i',
    'warning': '!',
    'menu': '=',
    'smiley': ':)',
    'mustache': '/\\/',
    'heart': '<3',
    'arrow_up': '^',
    'arrow_down': 'v',
    'arrow_left': '<',
    'arrow_right': '>',
    'radio_on': '(*)',
    'radio_off': '( )',
    'checkbox_on': '[x]',
    'checkbox_off': '[ ]',
    'checkbox_circle_on': '(x)',
    'checkbox_circle_off': '( )',
    'fancy_question_mark': '(?)',
    'neq': '!=',
    'geq': '>=',
    'leq': '<=',
    'times': 'x',
    'upper_block_1': '^',
    'upper_block_4': '^',
    'lower_block_1': '.',
    'lower_block_2': '_',
    'lower_block_3': '_',
    'lower_block_4': '=',
    'lower_block_5': '=',
    'lower_block_6': '*',
    'lower_block_7': '#',
    'lower_block_8': '#',
    'full_block': '#',
    'sup_0': '0',
    'sup_1': '1',
    'sup_2': '2',
    'sup_3': '3',
    'sup_4': '4',
    'sup_5': '5',
    'sup_6': '6',
    'sup_7': '7',
    'sup_8': '8',
    'sup_9': '9',
    'sup_minus': '-',
    'sup_plus': '+',
    'play': '>',
    'stop': '#',
    'record': 'o',
    'figure_dash': '-',
    'en_dash': '--',
    'em_dash': '---',
    'dquote_left': '"',
    'dquote_right': '"',
    'squote_left': "'",
    'squote_right': "'",
}


def _table() -> dict[str, str]:
    if is_utf8_output():
        return SYMBOL_UTF8
    return SYMBOL_ASCII


class Symbol:
    """Active binding. ``symbol["tick"]`` follows cli.unicode."""

    def __getitem__(self, name: str) -> str:
        return _table()[name]

    def __iter__(self):
        return iter(_table())

    def items(self):
        return _table().items()

    def keys(self):
        return _table().keys()

    def values(self):
        return _table().values()

    def __len__(self) -> int:
        return len(_table())


symbol = Symbol()


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        category = unicodedata.category(char)
        if unicodedata.combining(char) or category in ("Mn", "Me", "Cf", "Cc"):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def list_symbols() -> None:
    """Print the symbol table in two columns, as cli does."""

    items = list(_table().items())
    def rpad(text: str, width: int) -> str:
        return text + (" " * max(0, width - _display_width(text)))

    chars = [rpad(f"{glyph}\t{name}", 25) for name, glyph in items]
    if len(chars) % 2:
        chars.append("")
    half = len(chars) // 2
    lines = [f"{chars[i]}   {chars[i + half]}" for i in range(half)]
    print("\n".join(lines), end="")
