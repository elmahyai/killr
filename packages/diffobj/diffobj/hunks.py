"""Atomic hunks, context grouping, and hunk headers."""

from __future__ import annotations

from diffobj.ses import _frame, diff_myers

_MIN_WIDTH = 6


def _empty_range() -> list[int]:
    return [0, 0]


def _copy_hunk(hunk: dict) -> dict:
    out = dict(hunk)
    out["A"] = list(hunk["A"])
    out["B"] = list(hunk["B"])
    for key in (
        "tar.rng",
        "cur.rng",
        "tar.rng.sub",
        "cur.rng.sub",
        "tar.rng.trim",
        "cur.rng.trim",
    ):
        out[key] = list(hunk[key])
    return out


def _span(start: int, size: int) -> list[int]:
    if size <= 0:
        return []
    return list(range(start + 1, start + size + 1))


def as_hunks(script, mode: str) -> list[dict]:
    """Turn a Myers script into atomic hunks. Indices are 1-based."""

    rows = _frame(script)
    if not rows:
        return [
            {
                "id": 1,
                "A": [],
                "B": [],
                "context": True,
                "guide": False,
                "tar.rng": _empty_range(),
                "cur.rng": _empty_range(),
                "tar.rng.sub": _empty_range(),
                "cur.rng.sub": _empty_range(),
                "tar.rng.trim": _empty_range(),
                "cur.rng.trim": _empty_range(),
                "completely.empty": True,
            }
        ]
    sections = []
    for row in rows:
        if not sections or sections[-1][0]["section"] != row["section"]:
            sections.append([row])
        else:
            sections[-1].append(row)
    hunks = []
    for index, group in enumerate(sections, 1):
        deleted = [row for row in group if row["type"] == "Delete"]
        inserted = [row for row in group if row["type"] == "Insert"]
        matched = [row for row in group if row["type"] == "Match"]
        del_len = sum(row["len"] for row in deleted)
        ins_len = sum(row["len"] for row in inserted)
        mtc_len = sum(row["len"] for row in matched)
        if (del_len or ins_len) and mtc_len:
            raise RuntimeError("Logic Error: unknown edit types; contact maintainer.")
        tar_len = del_len + mtc_len
        cur_len = ins_len + mtc_len
        del_last = deleted[0]["last.a"] if deleted else group[0]["last.a"]
        ins_last = inserted[0]["last.b"] if inserted else group[0]["last.b"]
        tar = _span(del_last, tar_len)
        cur = [-item for item in _span(ins_last, cur_len)]
        context = bool(mtc_len)
        if mode == "context":
            vector_a, vector_b = tar, cur
        elif mode == "unified":
            vector_a = tar + ([] if context else cur)
            vector_b = []
        elif mode == "sidebyside":
            vector_a, vector_b = tar, cur
        else:
            raise RuntimeError("Logic Error: unknown mode; contact maintainer.")
        tar_rng = [del_last + 1, del_last + tar_len] if tar_len else _empty_range()
        cur_rng = [ins_last + 1, ins_last + cur_len] if cur_len else _empty_range()
        hunks.append(
            {
                "id": index,
                "A": vector_a,
                "B": vector_b,
                "context": context,
                "guide": False,
                "tar.rng": list(tar_rng),
                "cur.rng": list(cur_rng),
                "tar.rng.sub": list(tar_rng),
                "cur.rng.sub": list(cur_rng),
                "tar.rng.trim": list(tar_rng),
                "cur.rng.trim": list(cur_rng),
                "completely.empty": False,
            }
        )
    return hunks


def char_diff(left: list[str], right: list[str], etc) -> list[dict]:
    script = diff_myers(list(left), list(right), etc.max_diffs, False)
    return as_hunks(script, etc.mode)


def r_head(values, count: int):
    values = list(values)
    if count >= 0:
        return values[:count]
    return values[:count] if count != 0 else values


def r_tail(values, count: int):
    values = list(values)
    if count == 0:
        return []
    if count > 0:
        return values[-count:]
    return values[-count:]


def hunk_sub(hunk: dict, op: str, count: int) -> dict:
    hunk = _copy_hunk(hunk)
    start, end = hunk["tar.rng.sub"]
    if not start:
        return hunk
    length = end - start + 1
    extra = length - count
    if extra >= 0:
        if op == "head":
            hunk["A"] = r_head(hunk["A"], count)
            hunk["B"] = r_head(hunk["B"], count)
        else:
            hunk["A"] = r_tail(hunk["A"], count)
            hunk["B"] = r_tail(hunk["B"], count)
        if count:
            if op == "tail":
                hunk["tar.rng.sub"][0] = hunk["tar.rng.sub"][0] + extra
                hunk["tar.rng.trim"][0] = hunk["tar.rng.sub"][0]
                hunk["cur.rng.sub"][0] = hunk["cur.rng.sub"][0] + extra
                hunk["cur.rng.trim"][0] = hunk["cur.rng.sub"][0]
            else:
                hunk["tar.rng.sub"][1] = hunk["tar.rng.sub"][1] - extra
                hunk["tar.rng.trim"][1] = hunk["tar.rng.sub"][1]
                hunk["cur.rng.sub"][1] = hunk["cur.rng.sub"][1] - extra
                hunk["cur.rng.trim"][1] = hunk["cur.rng.sub"][1]
        else:
            empty = _empty_range()
            hunk["tar.rng.sub"] = list(empty)
            hunk["cur.rng.sub"] = list(empty)
            hunk["tar.rng.trim"] = list(empty)
            hunk["cur.rng.trim"] = list(empty)
    return hunk


def _alternates(flags: list[bool]) -> bool:
    if len(flags) < 2:
        return True
    return all(abs(int(flags[i + 1]) - int(flags[i])) == 1 for i in range(len(flags) - 1))


def process_hunks(hunks: list[dict], context: int) -> list[list[dict]]:
    flags = [hunk["context"] for hunk in hunks]
    if context < 0 or len(hunks) < 2 or not any(flags):
        groups = [[_copy_hunk(hunk) for hunk in hunks]]
    else:
        if not _alternates(flags):
            raise RuntimeError(
                "Logic Error: atomic hunks not interspersing context; contact maintainer."
            )
        groups = []
        index = 1 if flags[0] else 0
        while index < len(hunks):
            if index:
                group = [hunk_sub(hunks[index - 1], "tail", context), _copy_hunk(hunks[index])]
            else:
                group = [_copy_hunk(hunks[index])]
            while (
                index < len(hunks)
                and index + 2 < len(hunks)
                and len(hunks[index + 1]["A"]) <= context * 2
            ):
                group.append(_copy_hunk(hunks[index + 1]))
                if index < len(hunks) - 2:
                    group.append(_copy_hunk(hunks[index + 2]))
                index += 2
            if index < len(hunks) - 1:
                group.append(hunk_sub(hunks[index + 1], "head", context))
            groups.append(group)
            index += 2
    cursor = 1
    for group in groups:
        for hunk in group:
            hunk["id"] = cursor
            cursor += 1
    return groups


def context_lines(context, line_limit: list[int]) -> int:
    if isinstance(context, int):
        return context
    # AutoContext, or the string "auto" already resolved to one.
    if line_limit[0] < 0:
        return int(context.max)
    return int(context.max)


def group_hunks(hunks: list[dict], etc) -> list[list[dict]]:
    return process_hunks(hunks, context_lines(etc.context, etc.line_limit))


def rng_as_chr(rng: list[int]) -> str:
    if len(rng) < 2 or rng == [0, 0]:
        if len(rng) < 2:
            return "0"
    start, end = rng
    if end - start:
        width = (end - start + 1) if end else 0
        return f"{start},{width}"
    return str(start)


def _non_fill(rng: list[int], fills: list[int]) -> list[int]:
    if not rng or not rng[0]:
        return _empty_range()
    chosen = [item for item in range(rng[0], rng[1] + 1) if item not in fills]
    if not chosen:
        return _empty_range()
    return [chosen[0], chosen[-1]]


def make_headers(groups: list[list[dict]], mode: str, tar_fill: list[bool], cur_fill: list[bool]) -> list[list[str]]:
    headers = []
    tar_fills = [index for index, flag in enumerate(tar_fill, 1) if flag]
    cur_fills = [index for index, flag in enumerate(cur_fill, 1) if flag]
    flat = [hunk for group in groups for hunk in group]
    for group in groups:
        ids = [hunk["id"] for hunk in group if not hunk["guide"]]
        columns = []
        for hunk in flat:
            columns.append(
                [
                    _non_fill(hunk["tar.rng.sub"], tar_fills),
                    _non_fill(hunk["cur.rng.sub"], cur_fills),
                ]
            )
        tar = _find_rng(ids, [columns[hunk["id"] - 1][0] for hunk in flat])
        cur = _find_rng(ids, [columns[hunk["id"] - 1][1] for hunk in flat])
        tar_adj = _adjust_fill(tar, tar_fill)
        cur_adj = _adjust_fill(cur, cur_fill)
        if mode == "sidebyside":
            headers.append([f"@@ {rng_as_chr(tar_adj)} @@", f"@@ {rng_as_chr(cur_adj)} @@"])
        else:
            headers.append([f"@@ {rng_as_chr(tar_adj)} / {rng_as_chr(cur_adj)} @@"])
    return headers


def _find_rng(ids: list[int], ranges: list[list[int]]) -> list[int]:
    if not ids:
        return _empty_range()
    with_start = [item for item in ids if ranges[item - 1][0] > 0]
    if not with_start:
        return _empty_range()
    start = min(ranges[item - 1][0] for item in with_start)
    end = max(ranges[item - 1][1] for item in ids)
    return [start, end]


def _adjust_fill(rng: list[int], fill: list[bool]) -> list[int]:
    if not rng or not rng[0]:
        return _empty_range()
    running = []
    count = 0
    for flag in fill:
        count += int(not flag)
        running.append(count)
    if rng[0] > len(running):
        return _empty_range()
    end = rng[1] if rng[1] <= len(running) else len(running)
    return [running[rng[0] - 1], running[end - 1]]


def visible_indices(groups: list[list[dict]]) -> list[int]:
    indices = []
    for group in groups:
        for hunk in group:
            indices.extend(hunk["A"])
            indices.extend(hunk["B"])
    return indices


def max_column_width(groups, headers, tar_raw, cur_raw, etc) -> None:
    from diffobj.layout import chr_trim, nchar2

    sizes = []
    for index in visible_indices(groups):
        if index > 0:
            sizes.append(nchar2(tar_raw[index - 1], etc.sgr_supported))
        elif index < 0:
            sizes.append(nchar2(cur_raw[-index - 1], etc.sgr_supported))
    header_text = [line for pair in headers for line in pair]
    header_sizes = [
        nchar2(chr_trim(line, etc.line_width, etc.sgr_supported), etc.sgr_supported)
        for line in header_text
    ]
    floor = _MIN_WIDTH + etc.gutter_width
    max_col = max([0, floor, *sizes, *header_sizes])
    if max_col < etc.text_width:
        etc.text_width = max_col
    etc.line_width = etc.text_width + etc.gutter_width
