"""In-hunk word diffs and the atomic unwrap that realigns wrapped vectors."""

from __future__ import annotations

import re

from diffobj.hunks import as_hunks, r_head, r_tail
from diffobj.ses import diff_myers

_WORD = re.compile(r'\s*(?:"(?:[^"\\]|\\.)*"|[^\s"]+)')
_ALNUM = re.compile(r"[^0-9A-Za-z]+")


def _words(line: str) -> list[str]:
    found = []
    for match in _WORD.finditer(line):
        token = match.group(0).lstrip(" \t")
        if token:
            found.append(token)
    return found


def _find_interval(values: list[int], breaks: list[int]) -> list[int]:
    out = []
    for value in values:
        at = 0
        for index, edge in enumerate(breaks, 1):
            if edge <= value:
                at = index
            else:
                break
        out.append(at)
    return out


def _line_starts(ends: list[int]) -> list[int]:
    if not ends:
        return []
    return [1] + [item + 1 for item in ends[:-1]]


def _inds_pos(hunk: dict) -> list[int]:
    both = list(hunk["A"]) + list(hunk["B"])
    return [item for item in both if item > 0]


def _inds_neg(hunk: dict) -> list[int]:
    both = list(hunk["A"]) + list(hunk["B"])
    return [abs(item) for item in both if item < 0]


def _find_word_line(hunks, index: int, positive: bool, ends_a: list[int], ends_b: list[int]) -> list[int]:
    hunk = hunks[index]
    inds_a = _inds_pos(hunk) if positive else _inds_neg(hunk)
    inds_b = _inds_neg(hunk) if positive else _inds_pos(hunk)
    if (not hunk["context"]) and (not inds_a) and inds_b:
        prev_inds = []
        next_inds = []
        if index > 0:
            prev = hunks[index - 1]
            prev_inds = _inds_pos(prev) if positive else _inds_neg(prev)
        if index + 1 < len(hunks):
            nxt = hunks[index + 1]
            next_inds = _inds_pos(nxt) if positive else _inds_neg(nxt)
        low = min(inds_b)
        high = max(inds_b)
        starts_b = _line_starts(ends_b)
        add_left = max(prev_inds) if prev_inds and low not in starts_b else None
        add_right = min(next_inds) if next_inds and high not in ends_b else None
        if add_left is None and low not in starts_b:
            add_left = None
        if add_left is not None and add_right is not None:
            inds_a = list(range(add_left, add_right + 1))
        else:
            inds_a = [item for item in (add_left, add_right) if item is not None]
    found = _find_interval(inds_a, _line_starts(ends_a))
    return sorted({item for item in found if item})


def _reassign(lines: list[list[int]], context: list[bool]) -> list[list[int]]:
    owners = []
    flat = []
    for index, group in enumerate(lines, 1):
        for value in group:
            flat.append(value)
            owners.append(index)
    duplicated = []
    seen = set()
    for value in flat:
        if value in seen and value not in duplicated:
            duplicated.append(value)
        seen.add(value)
    updated = [list(group) for group in lines]
    lengths = [len(group) for group in lines]
    for value in duplicated:
        where = [owners[i] for i, item in enumerate(flat) if item == value]
        low, high = min(where), max(where)
        keep = None
        for index in range(low, high + 1):
            if (not context[index - 1]) and lengths[index - 1]:
                keep = index
                break
        if keep is None:
            for index in range(low, high + 1):
                if context[index - 1] and lengths[index - 1]:
                    keep = index
                    break
        if keep is not None:
            for index in range(low, high + 1):
                if index != keep:
                    updated[index - 1] = [item for item in updated[index - 1] if item != value]
    return updated


def _context_type(indices: list[int], diffs: set[int]) -> str:
    if not indices:
        return "both"
    flags = [item in diffs for item in indices]
    if flags[0] and flags[-1]:
        return "neither"
    if flags[0]:
        return "ends"
    if flags[-1]:
        return "starts"
    return "both"


def _pad_middle(values: list[int], pad: list) -> list:
    half = (len(values) + 1) // 2
    return list(values[:half]) + list(pad) + list(values[half // 1 and len(values) // 2 :])


def _pad_middle_r(values: list, pad: list) -> list:
    # c(head(vec, ceiling(length/2)), pad, tail(vec, floor(length/2)))
    head_n = (len(values) + 1) // 2
    tail_n = len(values) // 2
    return list(values[:head_n]) + list(pad) + list(values[len(values) - tail_n :])


def word_to_line_map(hunks, tar_dat, cur_dat, tar_ends, cur_ends):
    count = len(hunks)
    tar_lines = [
        _find_word_line(hunks, index, True, tar_ends, cur_ends) for index in range(count)
    ]
    cur_lines = [
        _find_word_line(hunks, index, False, cur_ends, tar_ends) for index in range(count)
    ]
    context = [bool(hunk["context"]) for hunk in hunks]
    tar_idx = []
    cursor = 1
    for end in tar_ends:
        tar_idx.append(list(range(cursor, end + 1)))
        cursor = end + 1
    cur_idx = []
    cursor = 1
    for end in cur_ends:
        cur_idx.append(list(range(cursor, end + 1)))
        cursor = end + 1
    tar_diff = []
    cur_diff = []
    for hunk, flag in zip(hunks, context):
        if flag:
            continue
        both = list(hunk["A"]) + list(hunk["B"])
        tar_diff.extend(abs(item) for item in both if item > 0)
        cur_diff.extend(abs(item) for item in both if item < 0)
    tar_diff_set = set(tar_diff)
    cur_diff_set = set(cur_diff)
    tar_mix = [_context_type(group, tar_diff_set) for group in tar_idx]
    cur_mix = [_context_type(group, cur_diff_set) for group in cur_idx]

    tar_lines = _reassign(tar_lines, context)
    cur_lines = _reassign(cur_lines, context)

    index = 0 if context[0] else 1
    while index < len(tar_lines):
        if tar_lines[index] == [] and cur_lines[index] == []:
            tar_lo = cur_lo = False
            if index:
                tar_lo = tar_lines[index - 1] == []
                cur_lo = cur_lines[index - 1] == []
            tar_hi = tar_lines[index + 1] == [] if index + 1 < len(tar_lines) else False
            cur_hi = cur_lines[index + 1] == [] if index + 1 < len(cur_lines) else False
            if (tar_lo or tar_hi) and (cur_lo or cur_hi):
                if tar_lo:
                    del tar_lines[index - 1 : index + 1]
                else:
                    del tar_lines[index : index + 2]
                if cur_lo:
                    del cur_lines[index - 1 : index + 1]
                else:
                    del cur_lines[index : index + 2]
                del context[index : index + 2]
                continue
        index += 1

    def _full(dat, ends, diffs):
        # Lines whose every word is a difference are not used to steal partners.
        if not ends:
            return set()
        counts = []
        previous = 0
        for end in ends:
            counts.append(end - previous)
            previous = end
        hits = [0] * len(ends)
        for word in diffs:
            at = _find_interval([word], _line_starts(ends))[0]
            if 1 <= at <= len(hits):
                hits[at - 1] += 1
        return {line for line, (hit, total) in enumerate(zip(hits, counts), 1) if hit and hit == total}

    tar_full = _full(tar_dat, tar_ends, tar_diff)
    cur_full = _full(cur_dat, cur_ends, cur_diff)

    def _steal(lines, at):
        lines = [list(group) for group in lines]
        if at + 1 < len(lines) and lines[at + 1]:
            lines[at] = lines[at + 1][:1]
            lines[at + 1] = lines[at + 1][1:]
        elif at > 0 and lines[at - 1]:
            lines[at] = lines[at - 1][-1:]
            lines[at - 1] = lines[at - 1][:-1]
        return lines

    for at, flag in enumerate(context):
        if flag:
            continue
        if (not tar_lines[at]) and cur_lines[at] and (at + 1) not in cur_full and at + 1 not in cur_full:
            # cur_full is 1-based line numbers, not hunk numbers. R compares the
            # hunk's line ids with tot.diff lines. Approximate with the hunk index
            # only when the recorded lines are entirely inside tot.diff.
            pass
        cur_only = bool(cur_lines[at]) and all(line in cur_full for line in cur_lines[at])
        tar_only = bool(tar_lines[at]) and all(line in tar_full for line in tar_lines[at])
        if (not tar_lines[at]) and cur_lines[at] and not cur_only:
            tar_lines = _steal(tar_lines, at)
        elif (not cur_lines[at]) and tar_lines[at] and not tar_only:
            cur_lines = _steal(cur_lines, at)

    tar_out = [list(group) for group in tar_lines]
    cur_out = [list(group) for group in cur_lines]
    for at in range(len(tar_out)):
        if len(tar_out[at]) == len(cur_out[at]):
            continue
        tar_long = len(tar_out[at]) > len(cur_out[at])
        long = tar_out[at] if tar_long else cur_out[at]
        short = cur_out[at] if tar_long else tar_out[at]
        long_type = [tar_mix[line - 1] if tar_long else cur_mix[line - 1] for line in long if isinstance(line, int)]
        short_type = ""
        if len(short) == 1 and isinstance(short[0], int):
            short_type = tar_mix[short[0] - 1] if not tar_long else cur_mix[short[0] - 1]
        pad = [None] * (len(long) - len(short))
        if at == 0 and len(tar_out) > 1:
            padded = pad + short
        elif at == len(tar_out) - 1:
            padded = short + pad
        elif context[at] or len(short) != 1:
            padded = _pad_middle_r(short, pad)
        else:
            if short_type == "ends" and long_type and long_type[0] in ("ends", "neither"):
                padded = pad + short
            else:
                padded = short + pad
        if tar_long:
            cur_out[at] = padded
        else:
            tar_out[at] = padded

    def _augment(dat, lines):
        flat = [item for group in lines for item in group]
        new = {}
        for key, values in dat.items():
            filled = []
            source = 0
            for item in flat:
                if item is None:
                    if key == "fill":
                        filled.append(True)
                    elif key == "word.ind":
                        filled.append(-1)
                    elif key == "tok.rat":
                        filled.append(1)
                    elif key in ("trim.ind.start",):
                        filled.append(1)
                    elif key == "trim.ind.end":
                        filled.append(0)
                    else:
                        filled.append("" if isinstance(values[0] if values else "", str) else False)
                else:
                    filled.append(values[source])
                    source += 1
            if source != len(values):
                raise RuntimeError("word-to-line map dropped or repeated a display line")
            new[key] = filled
        return new

    tar_aug = _augment(tar_dat, tar_out)
    cur_aug = _augment(cur_dat, cur_out)
    tar_match = []
    cur_match = []
    for flag, group in zip(context, tar_out):
        tar_match.extend([flag] * len(group))
    for flag, group in zip(context, cur_out):
        cur_match.extend([flag] * len(group))
    positive = sum(tar_match)
    negative = sum(not flag for flag in tar_match) + sum(not flag for flag in cur_match)
    strings = [f"~U{item:016d}~" for item in range(positive + negative)]
    pos_strings = strings[:positive]
    neg_strings = strings[positive:]
    tar_pos = 0
    for index, flag in enumerate(tar_match):
        if flag:
            tar_aug["comp"][index] = pos_strings[tar_pos]
            tar_pos += 1
    cur_pos = 0
    for index, flag in enumerate(cur_match):
        if flag:
            cur_aug["comp"][index] = pos_strings[cur_pos]
            cur_pos += 1
    tar_neg = [index for index, flag in enumerate(tar_match) if not flag]
    cur_neg = [index for index, flag in enumerate(cur_match) if not flag]
    for offset, index in enumerate(tar_neg):
        tar_aug["comp"][index] = neg_strings[offset]
    tail = neg_strings[len(neg_strings) - len(cur_neg) :]
    for offset, index in enumerate(cur_neg):
        cur_aug["comp"][index] = tail[offset]
    return tar_aug, cur_aug


def _eq_text(text: str, words: list[str]) -> str:
    """Drop differing tokens. Identity coloring leaves the visible line alone."""

    if not words:
        return text
    out = text
    for word in words:
        out = out.replace(word, "", 1)
    return out


def diff_words(tar_dat, cur_dat, tar_ind, cur_ind, etc, diff_mode: str):
    """Word-diff the selected lines. Wrap mode realigns atomic vector lines."""

    if not tar_ind and not cur_ind:
        return tar_dat, cur_dat
    tar_lines = [tar_dat["trim"][index - 1] for index in tar_ind]
    cur_lines = [cur_dat["trim"][index - 1] for index in cur_ind]
    tar_split = [_words(line) for line in tar_lines]
    cur_split = [_words(line) for line in cur_lines]
    tar_lens = [len(group) for group in tar_split]
    cur_lens = [len(group) for group in cur_split]
    tar_flat = [word for group in tar_split for word in group]
    cur_flat = [word for group in cur_split for word in group]
    tar_ends = []
    total = 0
    for size in tar_lens:
        total += size
        tar_ends.append(total)
    cur_ends = []
    total = 0
    for size in cur_lens:
        total += size
        cur_ends.append(total)

    local = etc.copy()
    local.mode = "context"
    local.context = -1
    local.line_limit = [-1, -1]
    local.hunk_limit = [-1, -1]
    script = diff_myers(tar_flat, cur_flat, etc.max_diffs, False)
    hunks = as_hunks(script, "context")

    if diff_mode == "wrap":
        subset_tar = {key: [tar_dat[key][index - 1] for index in tar_ind] for key in tar_dat}
        subset_cur = {key: [cur_dat[key][index - 1] for index in cur_ind] for key in cur_dat}
        mapped_tar, mapped_cur = word_to_line_map(hunks, subset_tar, subset_cur, tar_ends, cur_ends)
        return _splice(tar_dat, tar_ind, mapped_tar), _splice(cur_dat, cur_ind, mapped_cur)

    # Record differing tokens so equal-string alignment can ignore them.
    mismatched_tar = []
    mismatched_cur = []
    for hunk in hunks:
        if hunk["context"]:
            continue
        mismatched_tar.extend(item for item in hunk["A"] if item > 0)
        mismatched_cur.extend(abs(item) for item in hunk["B"] if item < 0)
    _paint(tar_dat, tar_ind, tar_ends, mismatched_tar, tar_split)
    _paint(cur_dat, cur_ind, cur_ends, mismatched_cur, cur_split)
    return tar_dat, cur_dat


def _paint(dat, indices, ends, mismatched, split):
    if not indices:
        return
    buckets = [0] + ends[:-1]
    lines = _find_interval(mismatched, [item + 1 for item in buckets]) if mismatched else []
    bad = {}
    for word, line in zip(mismatched, lines):
        bad.setdefault(line, []).append(word)
    for offset, index in enumerate(indices, 1):
        words = [split[offset - 1][item - 1] for item in bad.get(offset, []) if item - 1 < len(split[offset - 1])]
        # bad stores global word numbers; convert via the line's own tokens below.
        del words
    # Map global mismatch word numbers onto each selected line.
    starts = [1] + [end + 1 for end in ends[:-1]]
    for offset, (start, end, index) in enumerate(zip(starts, ends, indices), 1):
        tokens = split[offset - 1]
        dropped = [tokens[word - start] for word in mismatched if start <= word <= end]
        dat["word.ind"][index - 1] = dropped or -1
        dat["eq"][index - 1] = _eq_text(dat["trim"][index - 1], dropped)


def _splice(original, indices, mapped):
    if not indices:
        return original
    low = indices[0]
    high = indices[-1]
    out = {}
    for key, values in original.items():
        out[key] = list(values[: low - 1]) + list(mapped[key]) + list(values[high:])
    return out


def prepare_eq(dat, etc) -> None:
    ratios = []
    for words, text in zip(dat["word.ind"], dat["trim"]):
        if words in (-1, None) or words == []:
            ratios.append(1)
            continue
        total = max(len(_words(text)), len(words))
        ratios.append(max(0, (total - len(words)) / total) if total else 1)
    dat["tok.rat"] = ratios
    if etc.align_alnum_only:
        return


def equal_key(text: str, etc) -> str:
    if etc.align_alnum_only:
        return _ALNUM.sub("", text)
    return text
