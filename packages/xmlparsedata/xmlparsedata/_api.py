"""Convert R ``getParseData`` rows to the XML emitted by xmlparsedata."""

from __future__ import annotations

import re
from collections.abc import Mapping


xml_parse_token_map = {
    "'?'": "OP-QUESTION",
    "'~'": "OP-TILDE",
    "'+'": "OP-PLUS",
    "'-'": "OP-MINUS",
    "'*'": "OP-STAR",
    "'/'": "OP-SLASH",
    "':'": "OP-COLON",
    "'^'": "OP-CARET",
    "'$'": "OP-DOLLAR",
    "'@'": "OP-AT",
    "'('": "OP-LEFT-PAREN",
    "'['": "OP-LEFT-BRACKET",
    "';'": "OP-SEMICOLON",
    "'{'": "OP-LEFT-BRACE",
    "'}'": "OP-RIGHT-BRACE",
    "')'": "OP-RIGHT-PAREN",
    "'!'": "OP-EXCLAMATION",
    "']'": "OP-RIGHT-BRACKET",
    "','": "OP-COMMA",
    "'\\\\'": "OP-LAMBDA",
}

_CONTROL = re.compile(r"[\x01-\x08\x0b-\x1f]")


def _records(data):
    if hasattr(data, "to_dict"):
        try:
            return list(data.to_dict(orient="records"))
        except TypeError:
            pass
    if isinstance(data, Mapping):
        keys = list(data)
        return [dict(zip(keys, values)) for values in zip(*(data[k] for k in keys))]
    return [dict(row) for row in data]


def _r(value) -> str:
    return str(value)


def _encode(text) -> str:
    if text is None:
        return ""
    return (
        _CONTROL.sub("", str(text))
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def xml_parse_data(x, includeText=None, pretty=False) -> str:
    """Return xmlparsedata's XML representation of parse-data rows.

    ``x`` is an iterable of mappings with the columns returned by
    ``utils::getParseData`` (or a dataframe with ``to_dict``).
    """
    header = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<exprlist>\n'
    footer = "\n</exprlist>\n"
    rows = _records(x)
    if not rows:
        return header + footer

    has_text = "text" in rows[0] and includeText is not False
    maxcol = max(max(int(row["col1"]), int(row["col2"])) for row in rows) + 1
    entries = []
    for row in rows:
        terminal = bool(row["terminal"])
        token = xml_parse_token_map.get(str(row["token"]), str(row["token"]))
        line1, col1 = int(row["line1"]), int(row["col1"])
        line2, col2 = int(row["line2"]), int(row["col2"])
        start = line1 * maxcol + col1
        end = line2 * maxcol + col2
        tag = (
            f'<{token} line1="{line1}" col1="{col1}" line2="{line2}" '
            f'col2="{col2}" start="{start}" end="{end}">'
            + (_encode(row.get("text")) if has_text else "")
            + (f"</{token}>" if terminal else "")
        )
        entries.append((line1, col1, -line2, -col2, terminal, -start, tag))
        if not terminal:
            entries.append((
                line2, col2, -(line2 - 1), -(col2 - 1), True, -start,
                f"</{token}>",
            ))

    entries.sort(key=lambda item: item[:6])
    if pretty:
        depth = 0
        lines = []
        for *key, tag in entries:
            terminal = key[4]
            # R computes indentation from opening/closing events. This is
            # equivalent for the well-formed ordering produced above.
            if terminal and tag.startswith("</"):
                depth -= 1
            lines.append(" " * (2 * max(depth + 1, 0)) + tag)
            if not terminal:
                depth += 1
        body = "\n".join(lines)
    else:
        body = "\n".join(entry[-1] for entry in entries)
    return header + body + footer

