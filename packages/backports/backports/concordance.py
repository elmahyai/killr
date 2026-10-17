"""R concordance objects: parse, print, and match an output line."""

from __future__ import annotations

import re

from backports._values import BackportError

__all__ = [
    "Rconcordance",
    "as_character_rconcordance",
    "as_rconcordance",
    "as_rconcordance_default",
    "matchConcordance",
    "print_rconcordance",
]


class Rconcordance:
    def __init__(self, offset, src_file, src_line):
        self.offset = offset
        self.src_file = src_file
        self.src_line = list(src_line)

    def __repr__(self) -> str:
        return f"Rconcordance({self.src_file!r}, {len(self.src_line)} lines)"


def print_rconcordance(x, *_args):
    lines = x.src_line
    files = _rep_len(x.src_file, len(lines))
    width = max([7, *(len(str(item)) for item in files), *(len(str(item)) for item in lines)] or [7])
    print(f"{'srcFile':>{width}} {'srcLine':>7}")
    for index, (src_file, src_line) in enumerate(zip(files, lines), start=1):
        label = index + (x.offset or 0)
        print(f"{label:>3} {src_file:>{width}} {src_line:>7}")
    return x


def as_character_rconcordance(x, targetfile="", *_args):
    offset = x.offset or 0
    src = list(x.src_line)
    srcfile = _rep_len(x.src_file, len(src))
    result = []
    while src:
        if len(set(srcfile)) > 1:
            n = next(i for i, name in enumerate(srcfile) if name != srcfile[0])
        else:
            n = len(srcfile)
        diffs = [src[i] - src[i - 1] for i in range(1, n)]
        lengths, values = _rle(diffs)
        vals = []
        for length, value in zip(lengths, values):
            vals.extend((length, value))
        head = f"concordance:{targetfile}:{srcfile[0]}:"
        if offset:
            head += f"ofs {offset}:"
        body = str(src[0])
        if vals:
            body += " " + " ".join(str(int(item)) for item in vals)
        result.append(head + body)
        offset += n
        src = src[n:]
        srcfile = srcfile[n:]
    return result[0] if len(result) == 1 else result


def as_rconcordance(x, *_args):
    if isinstance(x, Rconcordance):
        return x
    return as_rconcordance_default(x)


def as_rconcordance_default(x, *_args):
    texts = x if isinstance(x, (list, tuple)) else [x]
    cleaned = []
    for item in texts:
        if not isinstance(item, str):
            continue
        trimmed = re.sub(r"[^0-9]*$", "", item)
        cleaned.append(re.sub(r"^.*(concordance)", "concordance", trimmed, count=1))
    rows = [item for item in cleaned if item.startswith("concordance:")]
    if not rows:
        return None
    result = _string_to_concordance(rows[0])
    for line in rows[1:]:
        result = _add_concordance(result, line)
    return result


def matchConcordance(linenum, concordance):
    names = ("offset", "srcLine", "srcFile")
    if not all(hasattr(concordance, attr) or (isinstance(concordance, dict) and name in concordance) for attr, name in (
        ("offset", "offset"),
        ("src_line", "srcLine"),
        ("src_file", "srcFile"),
    )):
        if not isinstance(concordance, Rconcordance):
            raise BackportError("concordance is not valid")
    lines = [float(item) for item in (linenum if isinstance(linenum, (list, tuple)) else [linenum])]
    src_lines = list(concordance.src_line)
    src_file = _rep_len(concordance.src_file, len(src_lines))
    offset = concordance.offset or 0
    rows = []
    for line in lines:
        if line <= offset:
            rows.append(("", ""))
            continue
        index = int(line - offset) - 1
        rows.append((src_file[index], str(src_lines[index])))
    if isinstance(linenum, (list, tuple)):
        return rows
    return rows[0]


def _string_to_concordance(text: str) -> Rconcordance:
    parts = text.split(":")
    src_file = parts[2]
    if len(parts) == 4:
        offset = 0
        payload = parts[3]
    else:
        offset = int(re.sub(r"^ofs ([0-9]+)", r"\1", parts[3]))
        payload = parts[4]
    values = [int(item) for item in payload.split(" ") if item != ""]
    first = values[0]
    rest = values[1:]
    lengths = rest[0::2]
    diffs_values = rest[1::2]
    diffs = []
    for length, value in zip(lengths, diffs_values):
        diffs.extend([value] * length)
    src_lines = [first]
    running = first
    for diff in diffs:
        running += diff
        src_lines.append(running)
    return Rconcordance(offset, src_file, src_lines)


def _add_concordance(conc: Rconcordance, text: str) -> Rconcordance:
    prev = _string_to_concordance(text)
    files = _rep_len(conc.src_file, len(conc.src_line))
    lines = list(conc.src_line)
    for index, (src_line, src_file) in enumerate(zip(prev.src_line, _rep_len(prev.src_file, len(prev.src_line)))):
        slot = prev.offset + index
        while len(lines) <= slot:
            lines.append(None)
            files.append(None)
        files[slot] = src_file
        lines[slot] = src_line
    conc.src_file = files
    conc.src_line = lines
    return conc


def _rle(values):
    if not values:
        return [], []
    lengths = []
    unique = []
    current = values[0]
    count = 1
    for value in values[1:]:
        if value == current:
            count += 1
        else:
            lengths.append(count)
            unique.append(current)
            current = value
            count = 1
    lengths.append(count)
    unique.append(current)
    return lengths, unique


def _rep_len(value, n):
    if isinstance(value, (list, tuple)):
        if not value:
            return [None] * n
        return [value[i % len(value)] for i in range(n)]
    return [value] * n
