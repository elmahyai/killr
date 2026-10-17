"""Argument checks and the plain-text style used by the formatted diffs."""

from __future__ import annotations

from diffobj.context import AutoContext, auto_context
from diffobj.options import gdo

_MISSING = object()

MODES = ("auto", "unified", "context", "sidebyside")
PAGERS = ("auto", "off", "on")

_MODE_ERROR = (
    "Argument `mode` must be character(1L) and in "
    '`c("auto", "unified", "context", "sidebyside")`.'
)
_PAGER_ERROR = (
    "Argument `pager` must be one of `c(\"auto\", \"off\", \"on\")`, "
    "a `Pager` object, or a list."
)

_DOTTED = {
    "color.mode": "color_mode",
    "word.diff": "word_diff",
    "max.diffs": "max_diffs",
    "disp.width": "disp_width",
    "tar.banner": "tar_banner",
    "cur.banner": "cur_banner",
    "ignore.white.space": "ignore_white_space",
    "convert.hz.white.space": "convert_hz_white_space",
    "line.limit": "line_limit",
    "hunk.limit": "hunk_limit",
    "tab.stops": "tab_stops",
    "strip.sgr": "strip_sgr",
    "sgr.supported": "sgr_supported",
    "unwrap.atomic": "unwrap_atomic",
    "term.colors": "term_colors",
    "palette.of.styles": "palette_of_styles",
}

_GUTTER_TOKENS = {
    "insert": ">",
    "insert.ctd": ":",
    "delete": "<",
    "delete.ctd": ":",
    "match": " ",
    "match.ctd": " ",
    "guide": "~",
    "guide.ctd": "~",
    "fill": "~",
    "fill.ctd": "~",
    "context.sep": "~",
    "context.sep.ctd": "~",
}


class DiffError(ValueError):
    """An R ``stop()`` from the diff functions."""


def normalize_kwargs(kwargs: dict) -> dict:
    """Accept R dotted names as aliases of the snake_case parameters."""

    out = dict(kwargs)
    for dotted, snake in _DOTTED.items():
        if dotted not in out:
            continue
        if snake in out:
            raise DiffError(f"Argument `{dotted}` was given twice.")
        out[snake] = out.pop(dotted)
    return out


def _match_mode(mode) -> str:
    if not isinstance(mode, str) or mode == "" or any(ch == "\0" for ch in mode):
        raise DiffError(_MODE_ERROR)
    hits = [name for name in MODES if name[: len(mode)] == mode]
    if len(hits) != 1 and mode not in MODES:
        # R keeps the first prefix hit. An exact member is that member.
        if not hits:
            raise DiffError(_MODE_ERROR)
    if not hits:
        raise DiffError(_MODE_ERROR)
    return hits[0]


def _as_limit(value, name: str) -> list[int]:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        nums = [value]
    elif isinstance(value, (list, tuple)) and 1 <= len(value) <= 2:
        nums = list(value)
    else:
        raise DiffError(
            f"Argument `{name}` must be an integer vector of length 1 or 2 "
            "and if length 2, with the first value larger than or equal to "
            "the second."
        )
    out = []
    for item in nums:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise DiffError(
                f"Argument `{name}` must be an integer vector of length 1 or 2 "
                "and if length 2, with the first value larger than or equal to "
                "the second."
            )
        if isinstance(item, float) and item != int(item):
            raise DiffError(
                f"Argument `{name}` must be an integer vector of length 1 or 2 "
                "and if length 2, with the first value larger than or equal to "
                "the second."
            )
        out.append(int(item))
    if len(out) == 2 and out[1] > out[0]:
        raise DiffError(
            f"Argument `{name}` must be an integer vector of length 1 or 2 "
            "and if length 2, with the first value larger than or equal to "
            "the second."
        )
    if len(out) == 1:
        out = [out[0], out[0]]
    return out


def _banner(value, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise DiffError(
        "Argument `tar.banner` must be atomic and length(1L), NULL, a symbol, or a call"
        if False
        else "Argument `banner` must be atomic and length(1L), NULL, a symbol, or a call"
    )


def raw_gutter() -> dict:
    """StyleText tokens, ``format``-padded, then a gutter pad space."""

    width = max(len(token) for token in _GUTTER_TOKENS.values())
    padded = {name: token.ljust(width) + " " for name, token in _GUTTER_TOKENS.items()}
    padded["width"] = max(len(token) for token in padded.values())
    return padded


class Settings:
    """The pieces of ``Settings`` the formatter reads."""

    def __init__(self, **fields):
        self.__dict__.update(fields)

    def copy(self) -> "Settings":
        return Settings(**self.__dict__)


def resolve_settings(
    *,
    mode,
    context,
    format,
    pager,
    word_diff,
    max_diffs,
    disp_width,
    ignore_white_space,
    convert_hz_white_space,
    line_limit,
    hunk_limit,
    tar_banner,
    cur_banner,
    unwrap_atomic,
    tab_stops,
    align,
    strip_sgr,
    sgr_supported,
    guides,
    trim,
) -> Settings:
    if mode is None:
        mode = gdo("mode")
    mode = _match_mode(mode)

    if pager is None:
        pager = gdo("pager")
    if not isinstance(pager, str) or pager not in PAGERS:
        raise DiffError(_PAGER_ERROR)
    # Non-interactive "auto" is off. "on" still returns the lines; nothing is paged.
    page = False

    if format is None:
        format = gdo("format")
    if not isinstance(format, str):
        raise DiffError("Argument `format` must be character(1L) and not NA")

    if context is None:
        context = gdo("context")
    if isinstance(context, str):
        if context != "auto":
            raise DiffError(
                "Argument `context` must be integer(1L) and not NA, an object produced "
                "by `auto_context`, or \"auto\"."
            )
        context_value = auto_context()
    elif isinstance(context, AutoContext):
        context_value = context
    elif isinstance(context, bool) or not isinstance(context, (int, float)):
        raise DiffError(
            "Argument `context` must be integer(1L) and not NA, an object produced "
            "by `auto_context`, or \"auto\"."
        )
    else:
        context_value = int(context)

    if word_diff is None:
        word_diff = gdo("word.diff")
    if unwrap_atomic is None:
        unwrap_atomic = gdo("unwrap.atomic")
    if ignore_white_space is None:
        ignore_white_space = gdo("ignore.white.space")
    if convert_hz_white_space is None:
        convert_hz_white_space = gdo("convert.hz.white.space")
    for name, flag in (
        ("word.diff", word_diff),
        ("unwrap.atomic", unwrap_atomic),
        ("ignore.white.space", ignore_white_space),
        ("convert.hz.white.space", convert_hz_white_space),
    ):
        if not isinstance(flag, bool):
            raise DiffError(f"Argument `{name}` must be TRUE or FALSE.")

    if max_diffs is None:
        max_diffs = gdo("max.diffs")
    if isinstance(max_diffs, bool) or not isinstance(max_diffs, (int, float)):
        raise DiffError("Argument `max.diffs` must be integer(1L) and not NA.")
    max_diffs = int(max_diffs)

    if disp_width is None:
        disp_width = gdo("disp.width")
    if disp_width is None:
        disp_width = 0
    if isinstance(disp_width, bool) or not isinstance(disp_width, (int, float)):
        raise DiffError("Arugment `disp.width` must be integer(1L) and 0, or between 10 and 10000")
    disp_width = int(disp_width)
    if disp_width != 0 and (disp_width < 10 or disp_width > 10000):
        raise DiffError("Arugment `disp.width` must be integer(1L) and 0, or between 10 and 10000")
    if disp_width == 0:
        disp_width = 80

    if line_limit is None:
        line_limit = gdo("line.limit")
    if hunk_limit is None:
        hunk_limit = gdo("hunk.limit")
    line_limit = _as_limit(line_limit, "line.limit")
    hunk_limit = _as_limit(hunk_limit, "hunk.limit")

    if tab_stops is None:
        tab_stops = gdo("tab.stops")
    if isinstance(tab_stops, bool) or isinstance(tab_stops, (int, float)):
        stops = [int(tab_stops)]
    elif isinstance(tab_stops, (list, tuple)) and tab_stops:
        stops = [int(item) for item in tab_stops]
    else:
        raise DiffError(
            "Argument `tab.stops` must be integer containing at least one value and "
            "with all values strictly positive"
        )
    if any(item <= 0 for item in stops):
        raise DiffError(
            "Argument `tab.stops` must be integer containing at least one value and "
            "with all values strictly positive"
        )

    if align is None:
        align = gdo("align")
    if align is None:
        threshold = float(gdo("align.threshold"))
        min_chars = int(gdo("align.min.chars"))
        alnum_only = bool(gdo("align.count.alnum.only"))
    elif isinstance(align, (int, float)) and not isinstance(align, bool):
        if not 0 <= float(align) <= 1:
            raise DiffError(
                'Argument `align` must be an "AlignThreshold" object or numeric(1L) '
                "and between 0 and 1."
            )
        threshold = float(align)
        min_chars = int(gdo("align.min.chars"))
        alnum_only = bool(gdo("align.count.alnum.only"))
    else:
        threshold = float(getattr(align, "threshold", gdo("align.threshold")))
        min_chars = int(getattr(align, "min_chars", gdo("align.min.chars")))
        alnum_only = bool(getattr(align, "count_alnum_only", gdo("align.count.alnum.only")))

    gutter = raw_gutter()
    gutter_width = gutter["width"]
    col_pad = 2
    half = int((disp_width - col_pad) / 2)
    min_width = 6
    line_width = max(disp_width, min_width + gutter_width)
    text_width = line_width - gutter_width
    line_width_half = max(half, min_width + gutter_width)
    text_width_half = line_width_half - gutter_width

    if mode == "auto" and disp_width < 80:
        mode = "unified"

    banner_tar = "target" if tar_banner is None else tar_banner
    banner_cur = "current" if cur_banner is None else cur_banner
    if not isinstance(banner_tar, str) or not isinstance(banner_cur, str):
        raise DiffError(
            "Argument `tar.banner` must be atomic and length(1L), NULL, a symbol, or a call"
        )

    if strip_sgr is None:
        strip_sgr = False
    if sgr_supported is None:
        sgr_supported = False

    return Settings(
        mode=mode,
        context=context_value,
        format=format,
        pager=pager,
        page=page,
        word_diff=word_diff,
        unwrap_atomic=unwrap_atomic,
        max_diffs=max_diffs,
        disp_width=disp_width,
        ignore_white_space=ignore_white_space,
        convert_hz_white_space=convert_hz_white_space,
        line_limit=line_limit,
        hunk_limit=hunk_limit,
        tab_stops=stops,
        align_threshold=threshold,
        align_min_chars=min_chars,
        align_alnum_only=alnum_only,
        tar_banner=banner_tar,
        cur_banner=banner_cur,
        gutter=gutter,
        gutter_width=gutter_width,
        line_width=line_width,
        text_width=text_width,
        line_width_half=line_width_half,
        text_width_half=text_width_half,
        strip_sgr=bool(strip_sgr),
        sgr_supported=bool(sgr_supported),
        guides=guides,
        trim=trim,
        pad_col="  ",
        context_sep="----------",
        na_sub="",
        blank_sub="",
        wrap=True,
        pad=True,
    )


def side_by_side(etc: Settings) -> Settings:
    etc.mode = "sidebyside"
    etc.text_width = etc.text_width_half
    etc.line_width = etc.line_width_half
    return etc


def require_pair(target, current) -> None:
    if target is _MISSING:
        raise DiffError('argument "target" is missing, with no default')
    if current is _MISSING:
        raise DiffError('argument "current" is missing, with no default')
