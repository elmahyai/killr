"""Latex encoding tables and deparsing of latex tag lists."""

import json
from pathlib import Path

_TABLES = json.loads((Path(__file__).resolve().parent / "latex_tables.json").read_text(encoding="utf-8"))
_SPECIALS = ["\\", "#", "$", "%", "&", "~", "_", "^", "{", "}"]
_MACRO_SKIP = {f"\\{item}" for item in _SPECIALS + ["(", ")"]}
_UTF8_EXTRA = {
    710: "{\\textasciicircum}",
    711: "{\\textasciicaron}",
    714: "{\\textasciitilde}",
    728: "{\\textasciibreve}",
    729: "{\\textperiodcentered}",
    733: "{\\textacutedbl}",
    8204: "{\\textcompwordmark}",
    8216: "{\\textquoteleft}",
    8217: "{\\textquoteright}",
    8220: "{\\textquotedblleft}",
    8221: "{\\textquotedblright}",
    8224: "{\\textdagger}",
    8226: "{\\textbullet}",
    8230: "{\\textellipsis}",
    8364: "{\\texteuro}",
}


def _match_arg(encoding):
    choices = ["latin1", "latin2", "latin9", "UTF-8", "utf8"]
    if encoding is None:
        return "latin1"
    hits = [choice for choice in choices if choice.startswith(encoding)]
    if len(hits) != 1:
        raise ValueError(f"encoding must be one of {', '.join(choices)}")
    return hits[0]


def _lookup(table, index):
    if index <= 0 or index > len(table):
        return ""
    return table[index - 1]


def _one_latin(text, table_name):
    table = _TABLES[table_name]
    return "".join(_lookup(table, byte) for byte in text.encode("latin-1"))


def _one_utf8(text):
    table = _TABLES["utf8"]
    pieces = []
    for code in (ord(char) for char in text):
        if code in _UTF8_EXTRA:
            piece = _UTF8_EXTRA[code]
        elif code < 512:
            piece = _lookup(table, code) or "?"
        else:
            piece = "?"
        pieces.append(piece)
    return "".join(pieces)


def encoded_text_to_latex(x, encoding="latin1"):
    """Map characters to the latex commands in the tools tables."""
    choice = _match_arg(encoding)
    values = [x] if isinstance(x, str) else list(x)
    if choice == "latin1":
        converted = [_one_latin(value, "latin1") for value in values]
    elif choice == "latin2":
        converted = [_one_latin(value, "latin2") for value in values]
    elif choice == "latin9":
        converted = [_one_latin(value, "latin9") for value in values]
    else:
        converted = [_one_utf8(value) for value in values]
    return converted[0] if isinstance(x, str) else converted


def _text(node):
    if isinstance(node, str):
        return node
    return node.get("text", "")


def deparse_latex(nodes, drop_braces=False):
    """Turn a latex tag list back into text."""
    result = []
    last = "TEXT"
    expect = False
    for node in nodes:
        if isinstance(node, str) or node.get("tag") is None:
            raise ValueError("Internal error, no tag")
        tag = node["tag"]
        text = _text(node)
        if tag in ("VERB", "MACRO", "COMMENT"):
            result.append(text)
        elif tag == "TEXT":
            if last == "MACRO" and expect and text[:1].isalpha():
                result.append(" ")
            result.append(text)
        elif tag == "BLOCK":
            body = node.get("body", [])
            if drop_braces and not expect:
                result.append(deparse_latex(body, drop_braces))
            else:
                result.append("{" + deparse_latex(body, drop_braces) + "}")
        elif tag == "ENVIRONMENT":
            name = node["name"]
            result.append("\\begin{" + name + "}" + deparse_latex(node.get("body", []), drop_braces) + "\\end{" + name + "}")
        elif tag == "MATH":
            result.append("$" + deparse_latex(node.get("body", []), drop_braces) + "$")
        elif tag == "DISPLAYMATH":
            result.append("$$" + deparse_latex(node.get("body", []), drop_braces) + "$$")
        elif tag == "DEFINITION":
            result.append(deparse_latex(node.get("body", []), drop_braces))
        else:
            raise ValueError("Internal error, no tag")
        if tag == "MACRO":
            expect = text not in _MACRO_SKIP
        else:
            expect = expect and tag in ("BLOCK", "COMMENT")
        last = tag
    return "".join(result)


_UTF8 = json.loads((Path(__file__).resolve().parent / "latex_utf8.json").read_text(encoding="utf-8"))
_LATEX_ARGS = {key: int(value) for key, value in _UTF8["args"].items()}
_LATEX_TABLE = _UTF8["table"]
_WHITESPACE = {" ", "\t", "\n"}


def _lookup_piece(arg):
    tag = arg["tag"]
    if tag in ("MACRO", "TEXT"):
        return arg.get("text", "")
    if tag == "BLOCK":
        body = arg.get("body", [])
        return deparse_latex(body, drop_braces=True) if body else " "
    return ""


def latex_to_utf8(nodes):
    """Replace known latex macros with Unicode characters."""
    if isinstance(nodes, dict):
        if nodes.get("tag") == "BLOCK":
            latex_to_utf8(nodes.get("body", []))
        return nodes
    i = 0
    while i < len(nodes):
        node = nodes[i]
        tag = node.get("tag")
        if tag == "MACRO":
            name = node.get("text", "")
            numargs = _LATEX_ARGS.get(name)
            if numargs is None:
                i += 1
                continue
            collected = []
            j = i
            get_next = True
            k = 0
            next_tag = "TEXT"
            next_chars = []
            while k < numargs:
                if get_next:
                    j += 1
                    if j >= len(nodes):
                        import warnings
                        warnings.warn(f"argument for {name} not found", stacklevel=2)
                        next_tag = "TEXT"
                        next_chars = []
                        next_obj = {"tag": "TEXT", "text": ""}
                    else:
                        next_obj = nodes[j]
                        next_tag = next_obj.get("tag")
                        next_chars = list(next_obj.get("text", "")) if next_tag == "TEXT" else []
                    get_next = False
                if next_tag == "TEXT":
                    character = next_chars.pop(0) if next_chars else ""
                    if not next_chars:
                        get_next = True
                    if character in _WHITESPACE:
                        continue
                    collected.append({"tag": "TEXT", "text": character})
                    k += 1
                elif next_tag == "COMMENT":
                    get_next = True
                elif next_tag == "MACRO":
                    collected.append(next_obj)
                    k += 1
                elif next_tag in ("BLOCK", "ENVIRONMENT", "MATH", "DISPLAYMATH"):
                    collected.append(latex_to_utf8(next_obj))
                    k += 1
                    get_next = True
                else:
                    raise ValueError("Internal error:  NULL tag")
            cursor = _LATEX_TABLE.get(name)
            for arg in collected:
                if cursor is None:
                    break
                piece = _lookup_piece(arg)
                cursor = cursor.get(piece) if isinstance(cursor, dict) else None
            if isinstance(cursor, str):
                nodes[i] = {"tag": "TEXT", "text": cursor}
                if numargs:
                    if next_tag == "TEXT" and next_chars:
                        nodes[j] = {"tag": "TEXT", "text": "".join(next_chars)}
                        j -= 1
                    while j > i:
                        del nodes[j]
                        j -= 1
                i += 1
            else:
                i = j + 1
        elif tag == "BLOCK":
            latex_to_utf8(node.get("body", []))
            i += 1
        else:
            i += 1
    return nodes
