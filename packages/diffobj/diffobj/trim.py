"""Columns to keep when a diff ignores unsemantic text.

``trim*`` returns one ``(start, end)`` pair per line. Both ends are 1-based
and inclusive, which is how R stores the two-column matrix. An empty string
has ``end`` 0. A missing string has ``end`` None, which is R's ``NA``.

The object is read the same way as in ``guidesPrint``: a list of strings is a
character vector, a dict is a named list, and ``dim`` marks a matrix or array.
"""

from __future__ import annotations

import re
import warnings

from diffobj.guides import (
    _any_na,
    _as_character,
    _diff,
    _dim,
    _dimnames,
    _elements,
    _grep,
    _grepl,
    _head_dimnames,
    _nchar,
    _nth,
    _r_length,
    _r_names,
    _rle,
    _slot_names,
    _stopifnot,
    _substr,
    _which,
    detect_array_guides,
    detect_list_guides,
    detect_matrix_guides,
    detect_s4_guides,
    is_array,
    is_atomic,
    is_default_show_obj,
    is_matrix,
    is_object,
    is_r_list,
    is_s4,
    is_ts,
    split_by_guides,
)

_PAT_ATOM = re.compile(r"^\s*\[[1-9][0-9]*\]\s")
_PAT_MAT = re.compile(r"^\s*\[[1-9]+[0-9]*,\]\s")
_PAT_TBL = re.compile(
    "^(?:\x1b\\[[^m]*m)?\\s*[1-9]+[0-9]*:?(?:\x1b\\[[^m]*m)?\\s"
)
_PAT_ATTR = re.compile(r'^attr\(,"(\\"|[^"])*"\)$')
_PAT_NUM = re.compile(r".*?([0-9]+).*")
_PAT_TBL_NUM = re.compile(r".*?(?:\x1b\[[^m]*m.*?)*([0-9]+).*")
_PAT_STR = re.compile(r"^ (?: \.\.)*(?:\$|-|@) ")


class _PatIndex(list):
    def __init__(self, values, pat=None):
        super().__init__(values)
        self.pat = pat


def _is_chr_1(value) -> bool:
    return isinstance(value, str)


def _sub_first(pattern: re.Pattern[str], text: str) -> str:
    return pattern.sub("", text, count=1)


def _first_number(pattern: re.Pattern[str], text: str) -> str:
    matched = pattern.search(text)
    if matched is None:
        return text
    return matched.group(1)


def _as_int(text: str) -> int | None:
    try:
        return int(text)
    except ValueError:
        return None


def up_to_attr(x) -> list[str | None]:
    """Drop the first ``attr(,"...")`` line and everything after it."""

    text = _as_character(x)
    attr_id = _grep(_PAT_ATTR, text)
    if attr_id and attr_id[0] > 1:
        return text[: attr_id[0] - 1]
    return text


def rle_sub(lengths: list[int], ind) -> list[list[int]]:
    """Indices of the original sequence covered by the selected runs."""

    if ind and isinstance(ind[0], bool):
        chosen = _which(ind)
    else:
        chosen = [int(value) for value in ind]
    if chosen:
        all_nonzero = all(value != 0 for value in chosen)
        # R parses ``!all(ind) > 0`` as ``(!all(ind)) > 0``.
        if ((not all_nonzero) > 0) or not all(step > 0 for step in _diff(chosen)):
            raise ValueError("Internal Error: `ind` should be monotonically increasing")
    if not lengths:
        return []
    ends = []
    total = 0
    for length in lengths:
        total += length
        ends.append(total)
    ranges = []
    start = 1
    for end in ends:
        ranges.append(list(range(start, end + 1)))
        start = end + 1
    return [ranges[index - 1] for index in chosen]


def flatten_list(obj) -> list:
    """Leaves of a plain list. Atomic vectors, objects, and empty lists stay whole."""

    if is_r_list(obj) and not is_object(obj) and _r_length(obj):
        flat = []
        for element in _elements(obj):
            flat.extend(flatten_list(element))
        return flat
    return [obj]


def which_atomic_rh(x) -> list[int]:
    """Lines whose ``[n]`` prefix is a real atomic row header."""

    text = _as_character(x)
    _stopifnot(not _any_na(text), "!anyNA(x) is not TRUE")
    body = up_to_attr(text)
    flags = _grepl(_PAT_ATOM, body)
    lengths, values = _rle(flags)
    if not any(values):
        return []
    first_block = values.index(True) + 1
    start = sum(lengths[: first_block - 1]) + 1
    width = lengths[first_block - 1]
    indices = list(range(start, start + width))
    rows = [body[index - 1] for index in indices]
    headers = []
    for row in rows:
        matched = _PAT_ATOM.search(row)
        headers.append(matched.group(0) if matched else "")
    if len({_nchar(header) for header in headers}) != 1:
        return []
    numbers = [_first_number(_PAT_NUM, header) for header in headers]
    steps = _diff([int(number) for number in numbers])
    if not (
        len(set(steps)) <= 1
        and numbers
        and numbers[0] == "1"
        and (len(indices) < 2 or all(step == 1 for step in _diff(indices)))
    ):
        return []
    return indices


def which_atomic_cont(x_chr, x) -> list[int]:
    """Atomic content lines. Named vectors are left untrimmed."""

    up_to_attr(_as_character(x_chr))
    if _r_names(x) is not None:
        return []
    return which_atomic_rh(x_chr)


def strip_atomic_rh(x) -> list[str | None]:
    text = _as_character(x)
    _stopifnot(not _any_na(text), "!anyNA(x) is not TRUE")
    where = which_atomic_rh(text)
    out = list(text)
    for index in where:
        out[index - 1] = _sub_first(_PAT_ATOM, out[index - 1])
    return out


def _unlist(ranges: list[list[int]]) -> list[int]:
    flat = []
    for chunk in ranges:
        flat.extend(chunk)
    return flat


def wtr_help(x, pat: str) -> list[int]:
    """Repeating numeric row-header positions for a wrapped table."""

    text = list(x)
    flags = _grepl(pat, text)
    lengths, values = _rle(flags)
    if not (any(values) and len(values) > 1 and values[1]):
        return []
    target = lengths[1]
    match_blocks = [value and length == target for value, length in zip(values, lengths)]
    alternating = [False, True] * ((len(match_blocks) + 1) // 2)
    alternating = alternating[: len(match_blocks)]
    match_break = [left != right for left, right in zip(match_blocks, alternating)]
    if any(match_break):
        match_valid = match_blocks[: min(_which(match_break)) - 1]
    else:
        match_valid = match_blocks
    positions = list(range(1, len(match_valid) + 1))
    interstitial = [
        index
        for index, valid in zip(positions, match_valid)
        if not valid and index > 1 and index != len(match_valid)
    ]
    if interstitial:
        widths = [lengths[index - 1] for index in interstitial]
        if len(set(widths)) != 1:
            return []
        covered = _unlist(rle_sub(lengths, interstitial))
        if not all(text[index - 1] is not None and re.match(r"^\s", text[index - 1]) for index in covered):
            return []
    if not any(match_valid):
        return []
    max_valid = max(_which(match_valid))
    run_pick = [
        index <= max_valid and value
        for index, value in zip(range(1, len(lengths) + 1), values)
    ]
    ranges = rle_sub(lengths, run_pick)
    rx = re.compile(pat)
    heads = [""] * len(text)
    for index, flag in enumerate(flags):
        if not flag or text[index] is None:
            continue
        matched = rx.search(text[index])
        if matched:
            heads[index] = matched.group(0)
    numbers = []
    for head in heads:
        if head == "":
            numbers.append(None)
        else:
            numbers.append(_as_int(_first_number(_PAT_TBL_NUM, head)))
    head_ranges = [[numbers[index - 1] for index in chunk] for chunk in ranges]
    if not head_ranges or any(None in chunk for chunk in head_ranges):
        return []
    same = all(chunk == head_ranges[0] for chunk in head_ranges)
    one_apart = all(
        all(right - left == 1 for left, right in zip(chunk, chunk[1:]))
        for chunk in head_ranges
    )
    if same and one_apart and head_ranges[0][0] == 1:
        return _unlist(ranges)
    return []


def which_table_rh(x) -> _PatIndex:
    text = _as_character(x)
    _stopifnot(not _any_na(text), "!anyNA(x) is not TRUE")
    found = wtr_help(text, _PAT_TBL.pattern)
    result = _PatIndex(found)
    if found:
        result.pat = _PAT_TBL.pattern
    return result


def strip_table_rh(x) -> list[str | None]:
    text = _as_character(x)
    where = which_table_rh(text)
    if not where:
        return text
    pat = where.pat
    if not _is_chr_1(pat):
        raise ValueError("Logic Error: unexpected row header pattern; contact maintainer.")
    rx = re.compile(pat)
    out = list(text)
    for index in where:
        out[index - 1] = _sub_first(rx, out[index - 1])
    return out


def _contiguous_from_start(matches: list[int]) -> list[int]:
    if len(matches) <= 1:
        return matches
    keep = [True]
    total = 0
    for step in _diff(matches):
        total += 0 if step == 1 else 1
        keep.append(total == 0)
    return [match for match, flag in zip(matches, keep) if flag]


def which_matrix_rh(x, dim_names_x) -> list[int]:
    text = _as_character(x)
    guides = detect_matrix_guides(text, dim_names_x)
    res: list[int] = []
    if not guides:
        return res
    pieces = split_by_guides(text, guides)
    if not pieces:
        raise ValueError("Logic Error: no matrix pieces")
    pat_ind = []
    for piece in pieces:
        pat_ind.append(_contiguous_from_start(_grep(_PAT_MAT, piece)))
    if not (
        all(found == pat_ind[0] for found in pat_ind)
        and (len(pat_ind[0]) == 1 or all(step == 1 for step in _diff(pat_ind[0])))
    ):
        return res
    if not pat_ind[0]:
        return res
    sample = [pieces[0][index - 1] for index in pat_ind[0]]
    piece_nums = [int(_first_number(_PAT_NUM, line)) for line in sample]
    if not (
        piece_nums
        and piece_nums[0] == 1
        and (len(piece_nums) == 1 or all(step == 1 for step in _diff(piece_nums)))
    ):
        return res
    for piece, found in zip(pieces, pat_ind):
        for index in found:
            res.append(piece.idx[index - 1])
    return res


def strip_matrix_rh(x, dim_names_x) -> list[str | None]:
    text = _as_character(x)
    out = list(text)
    for index in which_matrix_rh(text, dim_names_x):
        out[index - 1] = _sub_first(_PAT_MAT, out[index - 1])
    return out


def which_array_rh(x, dim_names_x) -> list[int]:
    text = _as_character(x)
    banners = detect_array_guides(text, dim_names_x)
    pieces = split_by_guides(text, banners)
    found = [which_matrix_rh(piece, _head_dimnames(dim_names_x, 2)) for piece in pieces]
    if found and all(item == found[0] for item in found):
        mapped = []
        for piece, local in zip(pieces, found):
            for index in local:
                mapped.append(piece.idx[index - 1])
        return mapped
    return []


def strip_array_rh(x, dim_names_x) -> list[str | None]:
    text = _as_character(x)
    out = list(text)
    for index in which_array_rh(text, dim_names_x):
        out[index - 1] = _sub_first(_PAT_MAT, out[index - 1])
    return out


def _substr_rows(text: Sequence[str | None], bounds) -> list[str | None]:
    return [_substr(line, start, end) for line, (start, end) in zip(text, bounds)]


def strip_list_rh(x, obj) -> list[str | None]:
    """Trim row headers inside each list component. The tags themselves stay."""

    text = _as_character(x)
    if not _r_length(obj):
        return text
    guides = detect_list_guides(text)
    pieces = split_by_guides(text, guides, drop_leading=False)
    elements = flatten_list(obj)
    first = _nth(obj, 1)
    offset = 1 if is_r_list(first) and not is_object(first) and _r_length(first) else 0
    if len(elements) != len(pieces) - offset:
        return text
    if offset:
        head = pieces[0]
        tail = pieces[offset:]
    else:
        head = None
        tail = pieces
    trimmed = [trimPrint(element, piece) for element, piece in zip(elements, tail)]
    without = [_substr_rows(piece, bounds) for piece, bounds in zip(tail, trimmed)]
    headers = [[text[index - 1]] for index in guides]
    combined = [*headers, *without]
    keys = [*range(1, len(guides) + 1), *range(1, len(guides) + 1)]
    order = sorted(range(len(keys)), key=lambda index: (keys[index], index))
    interleaved = [combined[index] for index in order if index < len(combined)]
    parts = []
    if head is not None:
        parts.append(list(head))
    parts.extend(interleaved)
    out: list[str | None] = []
    for part in parts:
        out.extend(part)
    return out


def strip_s4_rh(x, obj) -> list[str | None]:
    _stopifnot(is_s4(obj), "isS4(obj) is not TRUE")
    text = _as_character(x)
    slots = _slot_names(obj)
    if not slots:
        raise ValueError("Internal Error: s4 object w/o slots; contact maintainer")
    guides = detect_s4_guides(text, obj)
    pieces = split_by_guides(text, guides, drop_leading=False)
    slot_values = []
    slot_map = getattr(obj, "slots", {})
    for name in slots:
        slot_values.append(slot_map[name])
    trimmed = [trimPrint(element, piece) for element, piece in zip(slot_values, pieces)]
    without = []
    for piece, bounds in zip(pieces, trimmed):
        without.extend(_substr_rows(piece, bounds))
    if len(without) + len(guides) == len(text):
        out: list[str | None] = [None] * len(text)
        guide_set = set(guides)
        cursor = 0
        for index in range(1, len(text) + 1):
            if index in guide_set:
                out[index - 1] = text[index - 1]
            else:
                out[index - 1] = without[cursor]
                cursor += 1
        return out
    warnings.warn("Unable to detect S4 object guides.", stacklevel=2)
    return text


def trim_sub(obj_as_chr, obj_stripped) -> list[tuple[int | None, int | None]]:
    """Start and end of ``obj_stripped`` inside each original line."""

    original = _as_character(obj_as_chr, what="obj.as.chr")
    stripped = _as_character(obj_stripped, what="obj.stripped")
    if len(original) != len(stripped):
        raise ValueError(
            "Logic Error: trimmed string does not have same number of elements as "
            "original; contact maintainer"
        )
    starts = []
    ends = []
    comparable = []
    for raw, cut in zip(original, stripped):
        raw_n = _nchar(raw)
        cut_n = _nchar(cut)
        if raw_n is None or cut_n is None:
            starts.append(None)
            ends.append(None)
            comparable.append(None)
            continue
        start = raw_n - cut_n + 1
        end = start - 1 + cut_n
        starts.append(start)
        ends.append(end)
        comparable.append(_substr(raw, start, end) == cut)
    if any(item is None for item in comparable):
        raise ValueError("missing value where TRUE/FALSE needed")
    if not all(comparable):
        raise ValueError(
            "Logic Error: trimmed string is not a substring of orginal, "
            "contact maintainer"
        )
    return list(zip(starts, ends))


def trim_identity(obj, obj_as_chr) -> list[tuple[int | None, int | None]]:
    """Keep every character. ``end`` is R ``nchar``, so an empty string ends at 0."""

    del obj
    text = _as_character(obj_as_chr, what="obj.as.chr")
    return [(1, _nchar(line)) for line in text]


def trimPrint(obj, obj_as_chr) -> list[tuple[int | None, int | None]]:
    """Drop unsemantic row headers from printed output, then report what remains."""

    text = _as_character(obj_as_chr, what="obj.as.chr")
    dim = _dim(obj)
    if is_matrix(obj):
        stripped = strip_matrix_rh(text, _dimnames(obj))
    elif (dim is not None and len(dim) == 2) or (
        is_ts(obj) and getattr(obj, "frequency", 1) > 1
    ):
        stripped = strip_table_rh(text)
    elif is_array(obj):
        stripped = strip_array_rh(text, _dimnames(obj))
    elif is_atomic(obj):
        stripped = strip_atomic_rh(text)
    elif is_r_list(obj) and not is_object(obj):
        stripped = strip_list_rh(text, obj)
    elif is_s4(obj) and is_default_show_obj(obj):
        stripped = strip_s4_rh(text, obj)
    else:
        stripped = text
    return trim_sub(text, stripped)


def trimStr(obj, obj_as_chr) -> list[tuple[int | None, int | None]]:
    """Drop ``str`` tokens `` $``, ``..$``, ``..-``, and ``..@``."""

    del obj
    text = _as_character(obj_as_chr, what="obj.as.chr")
    stripped = []
    for line in text:
        if line is None:
            stripped.append(None)
        else:
            stripped.append(_PAT_STR.sub("", line))
    return trim_sub(text, stripped)


def trimChr(obj, obj_as_chr) -> list[tuple[int | None, int | None]]:
    return trim_identity(obj, obj_as_chr)


def trimDeparse(obj, obj_as_chr) -> list[tuple[int | None, int | None]]:
    return trim_identity(obj, obj_as_chr)


def trimFile(obj, obj_as_chr) -> list[tuple[int | None, int | None]]:
    return trim_identity(obj, obj_as_chr)
