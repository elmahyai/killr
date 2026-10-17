"""Turn grouped hunks into the character vector ``as.character`` returns."""

from __future__ import annotations

from diffobj.layout import chr_trim, render_gutters, rpad, wrap_pieces
from diffobj.worddiff import equal_key


def _get(index: int, tar: list, cur: list):
    if index > 0:
        return tar[index - 1]
    if index < 0:
        return cur[-index - 1]
    return None


def _align(indices_a, indices_b, tar, cur, etc, context: bool):
    fin_a = [_get(item, tar["fin"], cur["fin"]) for item in indices_a]
    fin_b = [_get(item, tar["fin"], cur["fin"]) for item in indices_b]
    fill_a = [_get(item, tar["fill"], cur["fill"]) for item in indices_a]
    fill_b = [_get(item, tar["fill"], cur["fill"]) for item in indices_b]
    if context or not indices_a or not indices_b:
        return [fin_a], [fin_b], fill_a, fill_b
    eq_a = [_get(item, tar["eq"], cur["eq"]) for item in indices_a]
    eq_b = [_get(item, tar["eq"], cur["eq"]) for item in indices_b]
    ratio_a = [_get(item, tar["tok.rat"], cur["tok.rat"]) for item in indices_a]
    ratio_b = [_get(item, tar["tok.rat"], cur["tok.rat"]) for item in indices_b]
    valid_b = []
    keys_b = []
    for offset, (text, ratio) in enumerate(zip(eq_b, ratio_b), 1):
        key = equal_key(text or "", etc)
        if len(key) >= etc.align_min_chars and (ratio or 0) >= etc.align_threshold:
            valid_b.append(offset)
            keys_b.append(key)
    align = [0] * len(eq_a)
    consumed = 0
    for offset, (text, ratio) in enumerate(zip(eq_a, ratio_a), 1):
        key = equal_key(text or "", etc)
        if len(key) < etc.align_min_chars or (ratio or 0) < etc.align_threshold:
            continue
        if consumed >= len(valid_b):
            break
        for cursor, candidate in enumerate(keys_b[consumed:], consumed):
            if candidate == key:
                align[offset - 1] = valid_b[cursor]
                consumed = cursor + 1
                break
    chunks_a = _split(fin_a, align)
    used = set(align)
    align_b = [offset if offset in used else 0 for offset in range(1, len(fin_b) + 1)]
    chunks_b = _split(fin_b, align_b)
    if len(chunks_a) != len(chunks_b):
        return [fin_a], [fin_b], fill_a, fill_b
    return chunks_a, chunks_b, fill_a, fill_b


def _split(values, marks):
    """Group lines the way ``align_split`` does, dropping the bookkeeping."""

    if not any(marks):
        return [list(values)]
    chunks = []
    bucket = []
    previous = 0
    for value, mark in zip(values, marks):
        if mark and previous and mark != previous:
            chunks.append(bucket)
            bucket = []
        if mark and not previous:
            if bucket:
                chunks.append(bucket)
                bucket = []
        bucket.append(value)
        if mark:
            previous = mark
    if bucket:
        chunks.append(bucket)
    return chunks or [[]]


def _rows_from_hunk(hunk, tar, cur, etc):
    mode = etc.mode
    if mode == "context":
        indices_a = _range_members(hunk["tar.rng.trim"], hunk["A"])
        indices_b = _range_members(hunk["cur.rng.trim"], hunk["B"])
    elif mode == "unified":
        # Unified stores current indices as negatives inside A.
        indices_a = [item for item in hunk["A"] if item > 0 and _in_range(item, hunk["tar.rng.trim"])]
        indices_b = [item for item in hunk["A"] if item < 0 and _in_range(item, hunk["cur.rng.trim"])]
    else:
        indices_a = [item for item in hunk["A"] if item > 0 and _in_range(item, hunk["tar.rng.trim"])]
        indices_b = [item for item in hunk["B"] if item < 0 and _in_range(item, hunk["cur.rng.trim"])]
    chunks_a, chunks_b, fill_a, fill_b = _align(
        indices_a, indices_b, tar, cur, etc, hunk["context"]
    )
    return chunks_a, chunks_b, fill_a, fill_b, hunk["context"], hunk["guide"]


def _in_range(index: int, rng: list[int]) -> bool:
    if not rng or not rng[0]:
        return False
    magnitude = abs(index)
    return rng[0] <= magnitude <= rng[1]


def _range_members(rng, pool):
    if not rng or not rng[0]:
        return []
    wanted = set(range(rng[0], rng[1] + 1))
    return [item for item in pool if abs(item) in wanted and ((item > 0) == (pool and pool[0] > 0) or item < 0)]


def _side_rows(chunks_a, chunks_b, fill_a, fill_b, context, guide):
    left_text, left_type = [], []
    right_text, right_type = [], []
    flat_a = []
    flat_b = []
    for left, right in zip(chunks_a, chunks_b):
        size = max(len(left), len(right))
        left = list(left) + [None] * (size - len(left))
        right = list(right) + [None] * (size - len(right))
        flat_a.extend(left)
        flat_b.extend(right)
    fill_left = []
    cursor = 0
    for value in flat_a:
        if value is None:
            fill_left.append(True)
        else:
            fill_left.append(bool(fill_a[cursor]) if cursor < len(fill_a) else False)
            cursor += 1
    fill_right = []
    cursor = 0
    for value in flat_b:
        if value is None:
            fill_right.append(True)
        else:
            fill_right.append(bool(fill_b[cursor]) if cursor < len(fill_b) else False)
            cursor += 1
    for value, is_fill in zip(flat_a, fill_left):
        left_text.append("" if value is None else value)
        left_type.append(_kind(guide, is_fill, context, "delete"))
    for value, is_fill in zip(flat_b, fill_right):
        right_text.append("" if value is None else value)
        right_type.append(_kind(guide, is_fill, context, "insert"))
    return [(left_text, left_type), (right_text, right_type)]


def _kind(guide, is_fill, context, change):
    if guide:
        return "guide"
    if is_fill:
        return "fill"
    if context:
        return "match"
    return change


def _one_column(chunks_a, chunks_b, fill_a, fill_b, context, guide, unified: bool):
    if not unified:
        left = [item for chunk in chunks_a for item in chunk]
        right = [item for chunk in chunks_b for item in chunk]
        left_type = [_kind(guide, False, context, "delete")] * len(left)
        right_type = [_kind(guide, False, context, "insert")] * len(right)
        text = left + ([None] if right else []) + right
        types = left_type + (["context.sep"] if right else []) + right_type
        return [(["----------" if kind == "context.sep" else ("" if item is None else item) for item, kind in zip(text, types)], types)]
    # Unified: deletes then inserts within each chunk, stable by chunk index.
    text = []
    types = []
    for left, right in zip(chunks_a, chunks_b):
        for item in left:
            text.append(item)
            types.append(_kind(guide, False, context, "delete"))
        for item in right:
            text.append(item)
            types.append(_kind(guide, False, context, "insert"))
    return [(text, types)]


def lines_of(prepared) -> list[str]:
    etc = prepared.etc
    tar, cur = prepared.tar, prepared.cur
    _finish(tar, etc)
    _finish(cur, etc)
    columns: list[list[str]] = []
    types: list[list[str]] = []
    width = 2 if etc.mode == "sidebyside" else 1
    columns = [[] for _ in range(width)]
    types = [[] for _ in range(width)]

    banner_width = etc.text_width if etc.wrap else 10**9
    ban_a = chr_trim(etc.tar_banner, banner_width, etc.sgr_supported)
    ban_b = chr_trim(etc.cur_banner, banner_width, etc.sgr_supported)
    if etc.mode == "sidebyside":
        columns[0].append(ban_a)
        types[0].append("delete")
        columns[1].append(ban_b)
        types[1].append("insert")
    else:
        columns[0].extend([ban_a, ban_b])
        types[0].extend(["delete", "insert"])

    for group, header in zip(prepared.groups, prepared.headers):
        if group and not group[0].get("completely.empty"):
            if etc.mode == "sidebyside":
                columns[0].append(header[0])
                types[0].append("header")
                columns[1].append(header[1])
                types[1].append("header")
            else:
                columns[0].append(header[0])
                types[0].append("header")
        atoms = []
        for hunk in group:
            atoms.append(_rows_from_hunk(hunk, tar, cur, etc))
        if etc.mode == "context":
            block = _context_block(atoms)
            columns[0].extend(block[0])
            types[0].extend(block[1])
        elif etc.mode == "unified":
            for chunks_a, chunks_b, fill_a, fill_b, context, guide in atoms:
                block = _one_column(chunks_a, chunks_b, fill_a, fill_b, context, guide, True)[0]
                columns[0].extend(block[0])
                types[0].extend(block[1])
        else:
            for chunks_a, chunks_b, fill_a, fill_b, context, guide in atoms:
                pair = _side_rows(chunks_a, chunks_b, fill_a, fill_b, context, guide)
                columns[0].extend(pair[0][0])
                types[0].extend(pair[0][1])
                columns[1].extend(pair[1][0])
                types[1].extend(pair[1][1])

    rendered = []
    for text, kind in zip(columns, types):
        pieces = []
        for item, name in zip(text, kind):
            limit = etc.line_width if name == "header" else etc.text_width
            wrapped = wrap_pieces("" if item is None else item, limit, etc.sgr_supported)
            if name == "context.sep":
                wrapped = [etc.context_sep]
            elif etc.pad and name != "context.sep":
                wrapped = [rpad(part, limit, etc.sgr_supported) for part in wrapped]
            gutter_rows = render_gutters([name], [len(wrapped)], [len(wrapped)], etc.gutter)
            # render_gutters returns one row of pieces; header gutter is empty.
            gutters = gutter_rows[0]
            if name == "header":
                gutters = [""] * len(wrapped)
            for gutter, part in zip(gutters, wrapped):
                pieces.append(f"{gutter}{part}")
        rendered.append(pieces)

    if etc.mode == "sidebyside":
        size = max(len(rendered[0]), len(rendered[1]))
        left = rendered[0] + [""] * (size - len(rendered[0]))
        right = rendered[1] + [""] * (size - len(rendered[1]))
        rows = [f"{a}{etc.pad_col}{b}" for a, b in zip(left, right)]
    else:
        rows = rendered[0]

    preface = []
    if not _any_diff(prepared.groups):
        preface.append(_no_diff_message(prepared))
    return preface + rows


def _context_block(atoms):
    left, right = [], []
    left_type, right_type = [], []
    for chunks_a, chunks_b, fill_a, fill_b, context, guide in atoms:
        for chunk in chunks_a:
            for item in chunk:
                if item is None:
                    continue
                left.append(item)
                left_type.append(_kind(guide, False, context, "delete"))
        for chunk in chunks_b:
            for item in chunk:
                if item is None:
                    continue
                right.append(item)
                right_type.append(_kind(guide, False, context, "insert"))
    text = left + (["----------"] if right else []) + right
    types = left_type + (["context.sep"] if right else []) + right_type
    return text, types


def _finish(dat, etc):
    finished = []
    for raw, start, end, middle in zip(
        dat["raw"], dat["trim.ind.start"], dat["trim.ind.end"], dat["trim"]
    ):
        prefix = raw[: max(start - 1, 0)]
        suffix = raw[end:]
        finished.append(f"{prefix}{middle}{suffix}")
    blanks = etc.blank_sub
    dat["fin"] = [blanks if raw == "" else line for raw, line in zip(dat["raw"], finished)]


def _any_diff(groups) -> bool:
    for group in groups:
        for hunk in group:
            if not hunk["context"]:
                return True
    return False


def _no_diff_message(prepared) -> str:
    same_orig = prepared.tar["orig"] == prepared.cur["orig"]
    same_comp = prepared.tar["comp"] == prepared.cur["comp"]
    message = "No visible differences between objects"
    if (not same_orig) and same_comp:
        return (
            message
            + ", but there are some differences suppressed by "
            "`ignore.white.space`, `convert.hz.white.space`, `strip.sgr`, "
            "and/or `trim`. Set all those arguments to FALSE to highlight "
            "the differences."
        )
    if prepared.target != prepared.current and not _equal_values(prepared.target, prepared.current):
        return message + ", but objects are *not* `all.equal`."
    return message + "."


def _equal_values(left, right) -> bool:
    try:
        return left == right
    except Exception:
        return False
