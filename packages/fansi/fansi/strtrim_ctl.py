"""Control-aware strtrim. strtrim2_ctl calls the wrap routine in src/wrap.c."""

from __future__ import annotations

from fansi._args import option, prepare
from fansi._const import WARN_ERROR, WARN_MASK
from fansi._read import coerce_texts, resolve_warn
from fansi.simple import dflt_term_cap
from fansi.strwrap_ctl import _MISSING, strtrim_width, strwrap_csi

def _trim(x, width, warn, tabs, stops, ctl, normalize, carry, terminate):
    texts = coerce_texts(x)
    checked = prepare(
        x=texts,
        warn=warn,
        ctl=ctl,
        tabs_as_spaces=tabs,
        tab_stops=stops,
        normalize=normalize,
        carry=carry,
        terminate=terminate,
        warn_mask=WARN_MASK,
        coerce_x=False,
    )
    pieces = strwrap_csi(
        texts,
        strtrim_width(width),
        0,
        0,
        "",
        "",
        True,
        b"",
        False,
        checked["tabs_as_spaces"],
        checked["tab_stops"],
        checked["warn_int"],
        [1],
        True,
        checked["ctl_int"],
        checked["normalize"],
        checked["carry"],
        checked["terminate"],
    )
    if checked["normalize"]:
        from fansi.strwrap_ctl import _normalize_vector

        cap = prepare(term_cap=option("fansi.term.cap", dflt_term_cap()), coerce_x=False)
        return _normalize_vector(pieces, WARN_MASK & WARN_ERROR, cap["term_cap_int"], None)
    return pieces


def strtrim2_ctl(
    x,
    width,
    warn=_MISSING,
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Trim each string to `width` display columns. Tabs can be expanded first."""
    warn = resolve_warn(warn, _MISSING)
    if tabs_as_spaces is _MISSING:
        tabs_as_spaces = option("fansi.tabs.as.spaces", False)
    if tab_stops is _MISSING:
        tab_stops = option("fansi.tab.stops", 8)
    if normalize is _MISSING:
        normalize = option("fansi.normalize", False)
    if carry is _MISSING:
        carry = option("fansi.carry", False)
    if terminate is _MISSING:
        terminate = option("fansi.terminate", True)
    return _trim(
        x, width, warn, tabs_as_spaces, tab_stops, ctl, normalize, carry, terminate
    )


def strtrim_ctl(
    x,
    width,
    warn=_MISSING,
    ctl="all",
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """Trim to `width`. C0 controls count as zero width."""
    kwargs = {"ctl": ctl}
    if warn is not _MISSING:
        kwargs["warn"] = warn
    if normalize is not _MISSING:
        kwargs["normalize"] = normalize
    if carry is not _MISSING:
        kwargs["carry"] = carry
    if terminate is not _MISSING:
        kwargs["terminate"] = terminate
    return strtrim2_ctl(x, width, **kwargs)


def strtrim2_sgr(
    x,
    width,
    warn=_MISSING,
    tabs_as_spaces=_MISSING,
    tab_stops=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """strtrim2_ctl that treats only SGR sequences as controls."""
    kwargs = {"ctl": "sgr"}
    if warn is not _MISSING:
        kwargs["warn"] = warn
    if tabs_as_spaces is not _MISSING:
        kwargs["tabs_as_spaces"] = tabs_as_spaces
    if tab_stops is not _MISSING:
        kwargs["tab_stops"] = tab_stops
    if normalize is not _MISSING:
        kwargs["normalize"] = normalize
    if carry is not _MISSING:
        kwargs["carry"] = carry
    if terminate is not _MISSING:
        kwargs["terminate"] = terminate
    return strtrim2_ctl(x, width, **kwargs)


def strtrim_sgr(
    x,
    width,
    warn=_MISSING,
    normalize=_MISSING,
    carry=_MISSING,
    terminate=_MISSING,
):
    """strtrim_ctl that treats only SGR sequences as controls."""
    kwargs = {"ctl": "sgr"}
    if warn is not _MISSING:
        kwargs["warn"] = warn
    if normalize is not _MISSING:
        kwargs["normalize"] = normalize
    if carry is not _MISSING:
        kwargs["carry"] = carry
    if terminate is not _MISSING:
        kwargs["terminate"] = terminate
    return strtrim_ctl(x, width, **kwargs)
