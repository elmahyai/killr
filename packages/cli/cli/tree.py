"""Draw a tree with the same box characters cli uses."""

from __future__ import annotations

from cli.ansi_text import ansi_substr
from cli.layout import console_width
from cli.unicode_output import is_utf8_output


def box_chars() -> dict:
    if is_utf8_output():
        return {"h": "─", "v": "│", "l": "└", "j": "├"}
    return {"h": "-", "v": "|", "l": "\\", "j": "+"}


def _columns(data):
    if isinstance(data, dict):
        ids = list(data["id"])
        kids = list(data["kids"])
        labels = list(data["label"]) if "label" in data else list(ids)
        trimmed = list(data["trimmed"]) if "trimmed" in data else list(labels)
        return ids, kids, labels, trimmed
    ids, kids, labels, trimmed = [], [], [], []
    for row in data:
        ids.append(row[0])
        kids.append(row[1])
        labels.append(row[2] if len(row) > 2 else row[0])
        trimmed.append(row[3] if len(row) > 3 else labels[-1])
    return ids, kids, labels, trimmed


def tree(data, root=None, style=None, width=None, trim=False):
    """Draw the tree. The first column is the id and the second is the children."""

    ids, kids, labels, trimlabs = _columns(data)
    if root is None:
        root = ids[0] if ids else None
    if width is None:
        width = console_width()
    style = style or box_chars()
    seen: list = []
    res: list[str] = []

    def draw(node, n=(), mx=(), used=()):
        try:
            num = ids.index(node)
        except ValueError:
            return
        prefix = []
        for i, (ni, mxi) in enumerate(zip(n, mx)):
            last = i == len(n) - 1
            if ni < mxi:
                prefix.append((style["j"] if last else style["v"]) + (style["h"] if last else " "))
            elif ni == mxi and last:
                prefix.append(style["l"] + style["h"])
            else:
                prefix.append("  ")
        root_seen = node in seen
        label = trimlabs[num] if trim and root_seen else labels[num]
        lines = str(label).split("\n") if label is not None else [""]
        prefix2 = []
        if len(lines) > 1:
            for i, (ni, mxi) in enumerate(zip(n, mx)):
                last = i == len(n) - 1
                if ni < mxi:
                    prefix2.append(style["v"] + " ")
                else:
                    prefix2.append("  ")
        head = "".join(prefix)
        rest = "".join(prefix2)
        res.append(head + lines[0])
        for extra in lines[1:]:
            res.append(rest + extra)
        if not trim and node in used:
            return
        if not trim or not root_seen:
            seen.append(node)
            children = list(kids[num] or [])
            for index, child in enumerate(children, start=1):
                draw(child, n + (index,), mx + (len(children),), used + (node,))

    if ids and root is not None:
        draw(root)
    return [ansi_substr(line, 1, width) for line in res]
