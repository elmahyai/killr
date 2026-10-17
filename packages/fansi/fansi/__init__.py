"""Python translation of the R package fansi."""

from fansi.has_ctl import has_ctl, has_sgr
from fansi.html_esc import html_esc
from fansi.make_styles import make_styles
from fansi.set_knit_hooks import set_knit_hooks
from fansi.to_html import sgr_to_html, to_html
from fansi.nchar_ctl import nchar_ctl, nchar_sgr, nzchar_ctl, nzchar_sgr
from fansi.normalize_state import normalize_state
from fansi.state_at_end import close_state, state_at_end
from fansi.unhandled_ctl import unhandled_ctl
from fansi.simple import (
    dflt_css,
    dflt_term_cap,
    fansi_lines,
    fansi_unicode_version,
    fwl,
    html_code_block,
    in_html,
    sgr_256,
    term_cap_test,
)
from fansi.strsplit_ctl import strsplit_ctl, strsplit_sgr
from fansi.substr_ctl import (
    substr2_ctl,
    substr2_ctl_replace,
    substr2_sgr,
    substr_ctl,
    substr_ctl_replace,
    substr_sgr,
)
from fansi.strtrim_ctl import strtrim2_ctl, strtrim2_sgr, strtrim_ctl, strtrim_sgr
from fansi.strwrap_ctl import strwrap2_ctl, strwrap2_sgr, strwrap_ctl, strwrap_sgr
from fansi.strip_ctl import strip_ctl, strip_sgr
from fansi.tabs_as_spaces import tabs_as_spaces
from fansi.trimws_ctl import trimws_ctl

__all__ = [
    "dflt_css",
    "dflt_term_cap",
    "fansi_lines",
    "fansi_unicode_version",
    "fwl",
    "has_ctl",
    "has_sgr",
    "close_state",
    "html_code_block",
    "html_esc",
    "in_html",
    "make_styles",
    "nchar_ctl",
    "normalize_state",
    "nchar_sgr",
    "nzchar_ctl",
    "nzchar_sgr",
    "set_knit_hooks",
    "sgr_256",
    "sgr_to_html",
    "state_at_end",
    "strip_ctl",
    "strip_sgr",
    "strsplit_ctl",
    "strsplit_sgr",
    "substr2_ctl",
    "substr2_ctl_replace",
    "substr2_sgr",
    "substr_ctl",
    "substr_ctl_replace",
    "substr_sgr",
    "strtrim2_ctl",
    "strtrim2_sgr",
    "strtrim_ctl",
    "strtrim_sgr",
    "strwrap2_ctl",
    "strwrap2_sgr",
    "strwrap_ctl",
    "strwrap_sgr",
    "tabs_as_spaces",
    "term_cap_test",
    "to_html",
    "trimws_ctl",
    "unhandled_ctl",
]
