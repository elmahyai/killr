"""Guide lines for a diff.

A guide is a context line kept even when it sits far from a change, such as a
column header. The ``guides*`` functions return 1-based indices into
``obj_as_chr``. An empty result is R's ``integer(0)``.

The first argument is the original object, because the R methods dispatch on
it:

* a list of strings is a character vector and has no names
* a dict is a named list; ``{}`` is an empty list
* an R list of character vectors is a list of those vectors, so ``list("a","b")``
  is ``[["a"], ["b"]]``
* an object with a ``dim`` of length 2 is a matrix, unless ``klass`` includes
  ``"data.frame"``
* an object with a longer ``dim`` is an array
* ``klass`` ``"ts"`` with ``frequency`` above 1 is a time series
* ``s4=True`` with ``rclass`` and ``slots`` is an S4 object

``dimnames`` is a list or dict of length 2 (or more for an array). Dict keys
are ``names(dimnames)``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from crayon import has_style, strip_style

_REG_R_IDENT = r"(?:\.[A-Za-z]|[A-Za-z])[A-Za-z0-9_.]*"
_LIST_GUIDE = re.compile(
    rf"^((\[\[\d+\]\])|(\${_REG_R_IDENT}))*(\$`.*`.*)?$"
)
_META = set("[](){}*+?.^$\\|")


class Section(list):
    """One piece of text split on guide lines, with original line indices."""

    def __init__(self, text: Sequence[str], idx: Sequence[int]):
        super().__init__(text)
        self.idx = list(idx)


def _stopifnot(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _as_character(value, *, what: str = "txt") -> list[str | None]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: list[str | None] = []
        for item in value:
            if item is None or isinstance(item, str):
                out.append(item)
            else:
                _stopifnot(False, f"is.character({what}) is not TRUE")
        return out
    _stopifnot(False, f"is.character({what}) is not TRUE")
    return []


def _any_na(text: Sequence[str | None]) -> bool:
    return any(item is None for item in text)


def _nchar(text: str | None) -> int | None:
    if text is None:
        return None
    return len(text)


def _substr(text: str | None, start: int | None, end: int | None) -> str | None:
    if text is None or start is None or end is None:
        return None
    if end < start:
        return ""
    size = len(text)
    if start < 1:
        start = 1
    if start > size:
        return ""
    if end > size:
        end = size
    return text[start - 1 : end]


def _grepl(pattern: re.Pattern[str] | str, text: Sequence[str | None]) -> list[bool]:
    rx = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)
    found = []
    for line in text:
        if line is None:
            found.append(False)
        else:
            found.append(rx.search(line) is not None)
    return found


def _grep(pattern: re.Pattern[str] | str, text: Sequence[str | None]) -> list[int]:
    return _which(_grepl(pattern, text))


def _which(flags: Sequence[bool]) -> list[int]:
    return [index + 1 for index, flag in enumerate(flags) if flag]


def _diff(values: Sequence[int]) -> list[int]:
    return [values[index + 1] - values[index] for index in range(len(values) - 1)]


def _cumsum(values: Sequence[int]) -> list[int]:
    total = 0
    out = []
    for value in values:
        total += value
        out.append(total)
    return out


def _rle(values: Sequence) -> tuple[list[int], list]:
    if not values:
        return [], []
    lengths = [1]
    grouped = [values[0]]
    for value in values[1:]:
        if value == grouped[-1]:
            lengths[-1] += 1
        else:
            grouped.append(value)
            lengths.append(1)
    return lengths, grouped


def _head(values: Sequence, count: int) -> list:
    if count < 0:
        if -count >= len(values):
            return []
        return list(values[:count])
    return list(values[:count])


def _tail(values: Sequence, count: int) -> list:
    if count <= 0:
        return []
    if count >= len(values):
        return list(values)
    return list(values[-count:])


def _rep(values: Sequence, times: int) -> list:
    if times <= 0:
        return []
    return list(values) * times


def _rep_each(values: Sequence, times: Sequence[int]) -> list:
    out = []
    for value, count in zip(values, times):
        out.extend([value] * count)
    return out


def _sequence(counts: Sequence[int]) -> list[int]:
    out = []
    for count in counts:
        out.extend(range(1, count + 1))
    return out


def _unique(values: Sequence) -> list:
    seen = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def _split(values: Sequence, groups: Sequence[int]) -> list[list]:
    buckets: dict[int, list] = {}
    for value, group in zip(values, groups):
        buckets.setdefault(group, []).append(value)
    return [buckets[key] for key in sorted(buckets)]


def _neutralize(text: str | Sequence[str]) -> str | list[str]:
    """Replace regex metacharacters with SOH, matching ``gsub`` of ``"\\\\\\1"``."""

    def one(value: str) -> str:
        return "".join("\x01" if char in _META else char for char in value)

    if isinstance(text, str):
        return one(text)
    return [one(value) for value in text]


def _dim(obj) -> tuple | None:
    if isinstance(obj, (str, bytes, dict)):
        return None
    dim = getattr(obj, "dim", None)
    if dim is None:
        return None
    return tuple(dim)


def _classes(obj) -> list[str]:
    if isinstance(obj, (str, bytes, int, float, bool)) or obj is None:
        return []
    klass = getattr(obj, "klass", None)
    if klass is None:
        klass = getattr(obj, "rclass", None) if getattr(obj, "s4", False) else None
    if klass is None:
        return []
    if isinstance(klass, str):
        return [klass]
    return [str(item) for item in klass]


def is_data_frame(obj) -> bool:
    return "data.frame" in _classes(obj)


def is_matrix(obj) -> bool:
    dim = _dim(obj)
    return dim is not None and len(dim) == 2 and not is_data_frame(obj)


def is_array(obj) -> bool:
    dim = _dim(obj)
    return dim is not None and len(dim) >= 1 and not is_data_frame(obj)


def is_ts(obj) -> bool:
    return "ts" in _classes(obj) or getattr(obj, "ts", False) is True


def is_s4(obj) -> bool:
    return getattr(obj, "s4", False) is True


def is_object(obj) -> bool:
    return is_s4(obj) or bool(_classes(obj))


def _atomic_scalar(value) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))


def is_r_list(obj) -> bool:
    """R ``is.list``: a dict or a list that is not an atomic vector or array."""

    if is_s4(obj):
        return False
    if is_data_frame(obj):
        return True
    if is_matrix(obj) or is_array(obj):
        return False
    if isinstance(obj, dict):
        return True
    if isinstance(obj, list) and not all(_atomic_scalar(item) for item in obj):
        return True
    return False


def is_atomic(obj) -> bool:
    if is_s4(obj) or is_data_frame(obj) or is_r_list(obj):
        return False
    if is_matrix(obj) or is_array(obj):
        return True
    if obj is None:
        return False
    if isinstance(obj, (str, bool, int, float)):
        return True
    if isinstance(obj, list) and all(_atomic_scalar(item) for item in obj):
        return True
    return False


def _elements(obj) -> list:
    if isinstance(obj, dict):
        return list(obj.values())
    if isinstance(obj, list):
        return list(obj)
    return [obj]


def _nth(obj, index: int):
    return _elements(obj)[index - 1]


def _r_length(obj) -> int:
    if isinstance(obj, (dict, list)):
        return len(obj)
    if obj is None:
        return 0
    return 1


def _r_names(obj):
    if isinstance(obj, dict):
        return list(obj.keys())
    if isinstance(obj, (str, bytes, int, float, bool)) or obj is None:
        return None
    return getattr(obj, "names", None)


def _dimnames(obj):
    if isinstance(obj, (str, bytes, int, float, bool)) or obj is None:
        return None
    return getattr(obj, "dimnames", None)


def _dn_names(dim_n):
    if dim_n is None:
        return None
    if isinstance(dim_n, dict):
        return list(dim_n.keys())
    names = getattr(dim_n, "names", None)
    if names is None:
        return None
    return list(names)


def _dn_values(dim_n) -> list:
    if dim_n is None:
        return []
    if isinstance(dim_n, dict):
        return list(dim_n.values())
    return list(dim_n)


def _dn_item(dim_n, index: int):
    """``dim.n[[index]]``. ``NULL[[i]]`` is NULL."""

    if dim_n is None:
        return None
    values = _dn_values(dim_n)
    if index < 1 or index > len(values):
        raise ValueError("subscript out of bounds")
    return values[index - 1]


def _is_character_vec(value) -> bool:
    if isinstance(value, str):
        return True
    if isinstance(value, (list, tuple)) and all(
        item is None or isinstance(item, str) for item in value
    ):
        return True
    return False


def _head_dimnames(dim_n, count: int):
    if dim_n is None:
        return None
    values = _dn_values(dim_n)[:count]
    names = _dn_names(dim_n)
    if isinstance(dim_n, dict):
        return dict(list(dim_n.items())[:count])
    if names is None:
        return values

    class _Named(list):
        pass

    named = _Named(values)
    named.names = list(names)[:count]
    return named


def _nzchar(value) -> bool:
    return isinstance(value, str) and value != ""


def _styled(text: list[str | None]) -> list[str | None]:
    flags = has_style(text)
    if isinstance(flags, bool):
        styled = flags
    else:
        styled = any(flags)
    if not styled:
        return text
    cleaned = strip_style(text)
    if isinstance(cleaned, str) or cleaned is None:
        return [cleaned]
    return list(cleaned)


def split_by_guides(txt, guides, drop_leading: bool = True) -> list[Section]:
    """Split ``txt`` on guide rows. Each piece keeps the source line numbers."""

    text = _as_character(txt)
    guide_list = list(guides)
    _stopifnot(not _any_na(text), "!anyNA(txt) is not TRUE")
    _stopifnot(
        all(isinstance(guide, int) and not isinstance(guide, bool) for guide in guide_list),
        "is.integer(guides) is not TRUE",
    )
    span = range(1, len(text) + 1)
    _stopifnot(
        all(guide in span for guide in guide_list),
        "all(guides %in% seq_along(txt)) is not TRUE",
    )
    if not guide_list:
        return [Section(text, list(range(1, len(text) + 1)))]

    guide_l = [0] * len(text)
    for guide in guide_list:
        guide_l[guide - 1] = 1
    prefix = 1 if guide_list[0] == 1 else 0
    steps = [1 if step == 1 else 0 for step in _diff(guide_l)]
    sections = _cumsum([prefix, *steps])
    drop = set(guide_list)
    kept_ids = []
    kept_sec = []
    kept_txt = []
    for index, (line, section) in enumerate(zip(text, sections), start=1):
        if index in drop:
            continue
        kept_ids.append(index)
        kept_sec.append(section)
        kept_txt.append(line)
    parts = _split(kept_txt, kept_sec)
    inds = _split(kept_ids, kept_sec)
    if drop_leading and kept_sec:
        keep = max(kept_sec)
        parts = _tail(parts, keep)
        inds = _tail(inds, keep)
    return [Section(part, ind) for part, ind in zip(parts, inds)]


def detect_2d_guides(txt) -> list[int]:
    """Row numbers that look like wrapped table headers."""

    text = _styled(_as_character(txt))
    res: list[int] = []
    first_spaces = _grep(r"^\s+\S+", text)
    if not first_spaces:
        return res
    first_space = min(first_spaces)
    banner = _grepl(r"^\S+|^\s+[0-9]+|^\s+---\s*$", text)
    space_rows = [
        (not flag) and index >= first_space
        for index, flag in enumerate(banner, start=1)
    ]
    if not any(space_rows) or all(space_rows):
        if space_rows:
            return [1]
        return res
    head_row = min(_which(space_rows))
    after = [
        (not space) and index > head_row
        for index, space in enumerate(space_rows, start=1)
    ]
    data_rows = _which(after)
    if not data_rows:
        return res
    first_row = min(data_rows)
    last_row = max(_which([not space for space in space_rows]))
    if last_row <= head_row:
        return res
    space_bw = space_rows[head_row - 1 : last_row]
    as_int = [1 if flag else 0 for flag in space_bw]
    group_steps = [1 if step == 1 else 0 for step in _diff(as_int)]
    groups = _cumsum([1, *group_steps])
    blocks = _split(space_bw, groups)
    seq_dat = [(sum(1 for flag in block if flag), sum(1 for flag in block if not flag)) for block in blocks]
    first = seq_dat[0]
    valid = [column == first for column in seq_dat]
    if not any(valid):
        return res
    flat = [value for column in seq_dat for value in column]
    summed = _cumsum(flat)
    ends = [summed[column * 2] for column, keep in enumerate(valid) if keep]
    res = [end + head_row - 1 for end in ends]
    if seq_dat[0][0] > 1:
        header_counts = [column[0] for column in seq_dat]
        # ``res`` is one entry per valid group. The R expression recycles when
        # an invalid group makes the lengths differ.
        base = []
        for index, count in enumerate(header_counts):
            base.append(res[index % len(res)] - count)
        res = [left + right for left, right in zip(_sequence(header_counts), _rep_each(base, header_counts))]
    return res


def detect_list_guides(txt) -> list[int]:
    """Lines that are list tags such as ``[[1]]`` or ``$name``."""

    text = _as_character(txt)
    if not text:
        return []
    has_pat = []
    for line in text:
        if not line:
            has_pat.append(False)
        else:
            has_pat.append(_LIST_GUIDE.search(line) is not None)
    has_chars = [False, *[bool(line) for line in text[:-1]]]
    has_pat_prev = [False, *has_pat[:-1]]
    valid = [
        pat and (not chars or prev)
        for pat, chars, prev in zip(has_pat, has_chars, has_pat_prev)
    ]
    if any(valid):
        lengths, values = _rle(valid)
        ends = _cumsum(lengths)
        # Keep only the last line of each run of tags.
        keep = {ends[index] for index, value in enumerate(values) if value}
        valid = [index in keep for index in range(1, len(valid) + 1)]
    return _which(valid)


def detect_matrix_guides(txt, dim_n) -> list[int]:
    """Column-header lines of a matrix, including wrapped blocks."""

    text = _as_character(txt)
    _stopifnot(not _any_na(text), "!anyNA(txt) is not TRUE")
    _stopifnot(
        dim_n is None
        or (
            isinstance(dim_n, (list, tuple, dict))
            and len(dim_n) == 2
        ),
        "is.null(dim.n) || (is.list(dim.n) && length(dim.n) == 2L) is not TRUE",
    )
    names = _dn_names(dim_n)
    row_n = None if names is None else names[0]
    col_n = None if names is None else names[1]
    if _nzchar(col_n):
        col_pat = rf"^\s{{2,}}{_neutralize(col_n)}$"
        col_header = _grepl(col_pat, text)
    else:
        col_header = [False] * len(text)
    if _nzchar(row_n):
        row_pat = rf"^{_neutralize(row_n)}\s+\S+"
        row_header = _grepl(row_pat, text)
    else:
        extra = None
        second = _dn_item(dim_n, 2)
        if second is not None and _is_character_vec(second):
            if isinstance(second, str):
                labels = [_neutralize(second)]
            else:
                labels = _neutralize([item for item in second if item is not None])
            extra = "|".join(["", *labels])
        pattern = r"^\s+(\[,[1-9]+[0-9]*\]" + (extra or "") + r")(\s|$)"
        row_header = _grepl(pattern, text)
    row_types = [0] * len(text)
    for index, flag in enumerate(row_header):
        if flag:
            row_types[index] = 1
    for index, flag in enumerate(col_header):
        if flag:
            row_types[index] = 2
    if names is None:
        mx_starts = _which([kind == 1 for kind in row_types])
    else:
        tmp = _which([kind == 2 for kind in row_types])
        row_at = _which(row_header)
        col_at = _which(col_header)
        if sum(row_header) == sum(col_header) and [item + 1 for item in col_at] == row_at:
            mx_starts = tmp
        else:
            mx_starts = []
    if not mx_starts:
        return []
    mx_start = mx_starts[0]
    later = [item for item in mx_starts if item > mx_start]
    mx_end = later[0] - 1 if later else len(text)
    pat_inds = list(range(mx_start, mx_end + 1))
    if not pat_inds:
        return []
    repeats = (len(text) - mx_start + 1) // len(pat_inds)
    template = _rep([row_types[index - 1] for index in pat_inds], repeats)
    compared = row_types[: len(template)]
    return [
        index + mx_start - 1
        for index, (left, right) in enumerate(zip(compared, template), start=1)
        if left == right and right != 0
    ]


def detect_array_guides(txt, dim_n) -> list[int]:
    """``, ,`` banners of a higher-dimensional array, when each slab matches."""

    text = _as_character(txt)
    names = _dn_names(dim_n)
    _stopifnot(
        dim_n is None or isinstance(dim_n, (list, tuple, dict)),
        "is.list(dim.n) || is.null(dim.n) is not TRUE",
    )
    _stopifnot(
        names is None or (len(names) > 2 and all(isinstance(name, str) for name in names)),
        "(is.character(n.d.n) && length(n.d.n) > 2L) || is.null(n.d.n) is not TRUE",
    )
    dim_guides = _which(_grepl(r"^, ,", text))
    blanks = _which([line == "" for line in text])
    if not dim_guides or not blanks:
        return []
    if not all(guide + 1 in blanks for guide in dim_guides):
        return []
    # ``length(unique(diff) == 1)`` is the number of distinct gaps. Any
    # positive count is TRUE in R, so two or more banners always pass.
    gaps = _diff(dim_guides)
    spacing = len(dim_guides) == 1 or len(_unique(gaps))
    if not spacing:
        return []
    dim_guide_fin = sorted([*dim_guides, *[guide + 1 for guide in dim_guides]])
    sub_dat = split_by_guides(text, dim_guide_fin)
    heads = [detect_matrix_guides(piece, _head_dimnames(dim_n, 2)) for piece in sub_dat]
    if not heads:
        return []
    if all(head == heads[0] for head in heads) and all(len(head) > 0 for head in heads):
        return dim_guide_fin
    return []


def is_default_show_obj(obj) -> bool:
    """TRUE when an S4 object uses the default ``show`` method."""

    _stopifnot(is_s4(obj), "isS4(obj) is not TRUE")
    return bool(getattr(obj, "default_show", True))


def _class_names(obj) -> list[str]:
    rclass = getattr(obj, "rclass", None)
    if rclass is None:
        rclass = _classes(obj)
    if isinstance(rclass, str):
        return [rclass]
    return [str(item) for item in rclass]


def _slot_names(obj) -> list[str]:
    slots = getattr(obj, "slots", None)
    if isinstance(slots, dict):
        return list(slots.keys())
    if slots is None:
        return []
    return list(slots)


def detect_s4_guides(txt, obj) -> list[int]:
    """Class and slot banners from the default S4 ``show`` method."""

    _stopifnot(is_s4(obj), "isS4(obj) is not TRUE")
    if not is_default_show_obj(obj):
        return []
    text = _as_character(txt)
    guides = [f'An object of class "{name}"' for name in _class_names(obj)]
    guides.extend(f'Slot "{name}":' for name in _slot_names(obj))
    located = _which([line in guides for line in text])
    found = [text[index - 1] for index in located]
    if found != guides:
        return []
    return located


def _guide_text(obj_as_chr) -> list[str]:
    text = _as_character(obj_as_chr, what="obj.as.chr")
    if _any_na(text):
        raise ValueError("Cannot compute guides if `obj.as.chr` contains NAs")
    return text


def guidesPrint(obj, obj_as_chr) -> list[int]:
    """Guide lines for ``diffPrint``."""

    text = _guide_text(obj_as_chr)
    dim = _dim(obj)
    if is_matrix(obj):
        return detect_matrix_guides(text, _dimnames(obj))
    if (dim is not None and len(dim) == 2) or (is_ts(obj) and getattr(obj, "frequency", 1) > 1):
        return detect_2d_guides(text)
    if is_array(obj):
        return detect_array_guides(text, _dimnames(obj))
    if is_r_list(obj):
        return detect_list_guides(text)
    if is_s4(obj):
        return detect_s4_guides(text, obj)
    return []


def guidesStr(obj, obj_as_chr) -> list[int]:
    """Last line of each top-level `` $`` run in ``str`` output."""

    del obj
    text = _guide_text(obj_as_chr)
    starts = [line.startswith(" $") for line in text]
    nxt = [*starts[1:], False]
    return [index + 1 for index, (flag, follow) in enumerate(zip(starts, nxt)) if flag and not follow]


def guidesChr(obj, obj_as_chr) -> list[int]:
    """Guide lines for a character diff. The default method finds none."""

    del obj, obj_as_chr
    return []


def guidesDeparse(obj, obj_as_chr) -> list[int]:
    """Guide lines for a deparse diff. The default method finds none."""

    del obj, obj_as_chr
    return []


def guidesFile(obj, obj_as_chr) -> list[int]:
    """Guide lines for a file diff. The default method finds none."""

    del obj, obj_as_chr
    return []
