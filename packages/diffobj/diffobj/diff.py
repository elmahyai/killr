"""Formatted diffs: diffChr, diffPrint, diffStr, diffDeparse, diffFile, diffCsv, diffObj."""

from __future__ import annotations

from diffobj.capt import (
    Call,
    DataFrame,
    atomic_row_headers,
    has_dim,
    r_deparse,
    r_print,
    r_str,
    read_csv_frame,
    read_lines,
    trim_atomic,
)
from diffobj.checkargs import (
    _MISSING,
    DiffError,
    normalize_kwargs,
    require_pair,
    resolve_settings,
    side_by_side,
)
from diffobj.context import console_lines
from diffobj.hunks import char_diff, group_hunks, make_headers, max_column_width
from diffobj.layout import (
    normalize_whitespace,
    split_new_line,
    strip_hz_control,
)
from diffobj.render import lines_of
from diffobj.worddiff import diff_words, prepare_eq

_KNOWN = {
    "mode",
    "context",
    "format",
    "brightness",
    "color_mode",
    "word_diff",
    "pager",
    "guides",
    "trim",
    "rds",
    "unwrap_atomic",
    "max_diffs",
    "disp_width",
    "ignore_white_space",
    "convert_hz_white_space",
    "tab_stops",
    "line_limit",
    "hunk_limit",
    "align",
    "style",
    "palette_of_styles",
    "frame",
    "interactive",
    "term_colors",
    "tar_banner",
    "cur_banner",
    "strip_sgr",
    "sgr_supported",
    "extra",
}


class Diff:
    """A formatted diff. ``.lines`` matches R's ``as.character``."""

    def __init__(self, lines: list[str]):
        self.lines = lines

    def __str__(self) -> str:
        return "\n".join(self.lines)

    def __repr__(self) -> str:
        return f"Diff({len(self.lines)} lines)"


class _Prepared:
    def __init__(self, etc, tar, cur, groups, headers, target, current):
        self.etc = etc
        self.tar = tar
        self.cur = cur
        self.groups = groups
        self.headers = headers
        self.target = target
        self.current = current


def _kwargs(kwargs):
    kwargs = normalize_kwargs(dict(kwargs))
    unknown = set(kwargs) - _KNOWN
    if unknown:
        name = sorted(unknown)[0]
        raise DiffError(f"unused argument ({name})")
    return kwargs


def _settings(kwargs, target, current):
    guides = kwargs.get("guides", True)
    trim = kwargs.get("trim", True)
    etc = resolve_settings(
        mode=kwargs.get("mode"),
        context=kwargs.get("context"),
        format=kwargs.get("format"),
        pager=kwargs.get("pager"),
        word_diff=kwargs.get("word_diff"),
        max_diffs=kwargs.get("max_diffs"),
        disp_width=kwargs.get("disp_width"),
        ignore_white_space=kwargs.get("ignore_white_space"),
        convert_hz_white_space=kwargs.get("convert_hz_white_space"),
        line_limit=kwargs.get("line_limit"),
        hunk_limit=kwargs.get("hunk_limit"),
        tar_banner=kwargs.get("tar_banner"),
        cur_banner=kwargs.get("cur_banner"),
        unwrap_atomic=kwargs.get("unwrap_atomic"),
        tab_stops=kwargs.get("tab_stops"),
        align=kwargs.get("align"),
        strip_sgr=kwargs.get("strip_sgr"),
        sgr_supported=kwargs.get("sgr_supported"),
        guides=guides,
        trim=trim,
    )
    return etc


def _dat(lines: list[str]) -> dict:
    return {
        "orig": list(lines),
        "raw": list(lines),
        "trim": list(lines),
        "trim.ind.start": [1] * len(lines),
        "trim.ind.end": [len(line) for line in lines],
        "comp": list(lines),
        "eq": list(lines),
        "fin": list(lines),
        "fill": [False] * len(lines),
        "word.ind": [-1] * len(lines),
        "tok.rat": [1.0] * len(lines),
    }


def _apply_trim(lines: list[str], spans: list[tuple[int, int]]) -> tuple[list[str], list[int], list[int]]:
    trimmed = []
    starts = []
    ends = []
    for line, (start, end) in zip(lines, spans):
        starts.append(start)
        ends.append(end)
        if start > end:
            trimmed.append("")
        else:
            trimmed.append(line[start - 1 : end])
    return trimmed, starts, ends


def _use_trim(target, current, tar_lines, cur_lines, kind: str, requested):
    if requested is False:
        return None
    if kind != "print":
        return None
    if not (_atomic(target) and _atomic(current)):
        return None
    return trim_atomic


def _atomic(value) -> bool:
    if isinstance(value, (str, dict, DataFrame, Call)):
        return False
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, (str, int, float, bool)) or item is None for item in value)
    return isinstance(value, (int, float, bool)) or value is None


def _prepare_text(target, current, tar_lines, cur_lines, etc, kind: str):
    tar_lines = split_new_line(list(tar_lines))
    cur_lines = split_new_line(list(cur_lines))
    if etc.convert_hz_white_space:
        tar_lines = [strip_hz_control(line, etc.tab_stops) for line in tar_lines]
        cur_lines = [strip_hz_control(line, etc.tab_stops) for line in cur_lines]
    tar = _dat(tar_lines)
    cur = _dat(cur_lines)
    trimmer = _use_trim(target, current, tar_lines, cur_lines, kind, etc.trim)
    if trimmer is not None:
        tar_trim, tar_start, tar_end = _apply_trim(tar_lines, trimmer(tar_lines))
        cur_trim, cur_start, cur_end = _apply_trim(cur_lines, trimmer(cur_lines))
        if tar_trim != tar_lines and cur_trim != cur_lines:
            tar["trim"] = tar_trim
            cur["trim"] = cur_trim
            tar["trim.ind.start"] = tar_start
            tar["trim.ind.end"] = tar_end
            cur["trim.ind.start"] = cur_start
            cur["trim.ind.end"] = cur_end
            tar["comp"] = list(tar_trim)
            cur["comp"] = list(cur_trim)
            tar["eq"] = list(tar_trim)
            cur["eq"] = list(cur_trim)
    if etc.ignore_white_space:
        tar["comp"] = [normalize_whitespace(line) for line in tar["comp"]]
        cur["comp"] = [normalize_whitespace(line) for line in cur["comp"]]
        tar["eq"] = list(tar["comp"])
        cur["eq"] = list(cur["comp"])
    if (
        etc.word_diff
        and etc.unwrap_atomic
        and _atomic(target)
        and _atomic(current)
        and not has_dim(target)
        and not has_dim(current)
        and kind == "print"
    ):
        tar_rows = atomic_row_headers(tar["raw"])
        cur_rows = atomic_row_headers(cur["raw"])
        if tar_rows and cur_rows and tar_rows == list(range(tar_rows[0], tar_rows[-1] + 1)):
            if cur_rows == list(range(cur_rows[0], cur_rows[-1] + 1)):
                tar, cur = diff_words(tar, cur, tar_rows, cur_rows, etc, "wrap")
    hunks = char_diff(tar["comp"], cur["comp"], etc)
    if etc.word_diff:
        wrapped = set(atomic_row_headers(tar["raw"])) if kind == "print" else set()
        wrapped_cur = set(atomic_row_headers(cur["raw"])) if kind == "print" else set()
        for hunk in hunks:
            if hunk["context"]:
                continue
            both = list(hunk["A"]) + list(hunk["B"])
            tar_ind = [item for item in both if item > 0 and item not in wrapped]
            cur_ind = [abs(item) for item in both if item < 0 and abs(item) not in wrapped_cur]
            if tar_ind or cur_ind:
                tar, cur = diff_words(tar, cur, tar_ind, cur_ind, etc, "hunk")
        prepare_eq(tar, etc)
        prepare_eq(cur, etc)
    groups = group_hunks(hunks, etc)
    headers = make_headers(groups, etc.mode, tar["fill"], cur["fill"])
    max_column_width(groups, headers, tar["raw"], cur["raw"], etc)
    return _Prepared(etc, tar, cur, groups, headers, target, current)


def _too_wide(lines: list[str], limit: int) -> bool:
    return any(len(line) > limit for line in lines)


def _finish_mode(etc, tar_lines, cur_lines, kind: str, dimensioned: bool):
    if etc.mode != "auto":
        if etc.mode == "sidebyside":
            side_by_side(etc)
        return
    if kind == "print" and not dimensioned:
        side_by_side(etc)
        return
    if kind == "str":
        side_by_side(etc)
        return
    if _too_wide(tar_lines, etc.text_width_half) or _too_wide(cur_lines, etc.text_width_half):
        etc.mode = "unified"
    else:
        side_by_side(etc)


def _emit(prepared) -> Diff:
    return Diff(lines_of(prepared))


def _character_lines(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if item is None:
                out.append("NA")
            elif isinstance(item, str):
                out.append(item)
            elif isinstance(item, bool):
                out.append("TRUE" if item else "FALSE")
            else:
                out.append(str(item))
        return out
    if value is None:
        return ["NA"]
    if isinstance(value, bool):
        return ["TRUE" if value else "FALSE"]
    return [str(value)]


def diffChr(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Diff character vectors element by element."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    etc = _settings(kwargs, target, current)
    tar_lines = _character_lines(target)
    cur_lines = _character_lines(current)
    _finish_mode(etc, tar_lines, cur_lines, "chr", False)
    return _emit(_prepare_text(target, current, tar_lines, cur_lines, etc, "chr"))


def diffPrint(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Diff the printed form of two objects."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    etc = _settings(kwargs, target, current)
    dimensioned = has_dim(target) or has_dim(current)
    if not dimensioned:
        _finish_mode(etc, [], [], "print", False)
    tar_lines = r_print(target, etc.text_width)
    cur_lines = r_print(current, etc.text_width)
    if dimensioned:
        _finish_mode(etc, tar_lines, cur_lines, "print", True)
    return _emit(_prepare_text(target, current, tar_lines, cur_lines, etc, "print"))


def diffStr(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Diff ``str`` output of two objects."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    etc = _settings(kwargs, target, current)
    _finish_mode(etc, [], [], "str", False)
    tar_lines = r_str(target, etc.text_width)
    cur_lines = r_str(current, etc.text_width)
    return _emit(_prepare_text(target, current, tar_lines, cur_lines, etc, "str"))


def diffDeparse(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Diff ``deparse`` output of two objects."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    etc = _settings(kwargs, target, current)
    tar_lines = r_deparse(target, 80)
    cur_lines = r_deparse(current, 80)
    _finish_mode(etc, tar_lines, cur_lines, "deparse", False)
    return _emit(_prepare_text(target, current, tar_lines, cur_lines, etc, "deparse"))


def diffFile(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Diff two text files."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    etc = _settings(kwargs, target, current)
    try:
        tar_lines = read_lines(target)
    except OSError:
        raise DiffError("Unable to read `target` file.") from None
    try:
        cur_lines = read_lines(current)
    except OSError:
        raise DiffError("Unable to read `current` file.") from None
    _finish_mode(etc, tar_lines, cur_lines, "file", False)
    return _emit(_prepare_text(tar_lines, cur_lines, tar_lines, cur_lines, etc, "file"))


def diffCsv(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Diff two CSV files by printing the data frames ``read.csv`` would build."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    try:
        tar_frame = read_csv_frame(target)
    except OSError:
        raise DiffError("Unable to read `target` file.") from None
    try:
        cur_frame = read_csv_frame(current)
    except OSError:
        raise DiffError("Unable to read `current` file.") from None
    return diffPrint(tar_frame, cur_frame, **kwargs)


def diffObj(target=_MISSING, current=_MISSING, **kwargs) -> Diff:
    """Pick ``diffPrint`` or ``diffStr``, whichever R's ``diffObj`` would show."""

    require_pair(target, current)
    kwargs = _kwargs(kwargs)
    if kwargs.get("extra"):
        raise DiffError("Argument `extra` must be empty in `diffObj`.")
    printed = diffPrint(target, current, **kwargs)
    structured = diffStr(target, current, **kwargs)
    if len(printed.lines) <= console_lines() / 2:
        return printed
    if len(structured.lines) < len(printed.lines):
        return structured
    return printed


diff_chr = diffChr
diff_print = diffPrint
diff_str = diffStr
diff_deparse = diffDeparse
diff_file = diffFile
diff_csv = diffCsv
diff_obj = diffObj
