"""R-compatible helpers shared by the sass font, layer, and output translations.

Each helper follows a sass 0.4.10 R function of the same role:
quote_css_font_families, font_dep_name, font_face_css, utils::URLencode,
htmltools attribute escaping, match.arg, and as.character for scalars.
"""

from __future__ import annotations

import re
import string
import warnings
from dataclasses import dataclass
from typing import Any

from ._common import FontCollection

SASS_VERSION = "0.4.10"
DISPLAY_CHOICES = ("swap", "auto", "block", "fallback", "optional")

# Characters utils::URLencode(reserved = FALSE) leaves alone.
_URL_KEEP = set("[]!$&'()*+,;=:/?@#" + string.ascii_letters + string.digits + "._~-")


@dataclass
class HtmlDep:
    """An html dependency, the Python form of an htmlDependency() object.

    kind is "face" (a font.css stylesheet), "link" (a stylesheet link in the
    head), "google_local" (a Google Fonts dependency that is built only when it
    is rendered, see font_google.render_google_local), or "html" (a dependency
    built by html_dependency()).

    stylesheet is the stylesheet text. src is the directory the dependency
    reads from, and stylesheet_name is the file in it. all_files mirrors
    htmlDependency(all_files =): when True, every file in src is part of the
    dependency.
    """

    name: str
    version: str
    kind: str
    href: str | None = None
    head: str | None = None
    stylesheet: str | None = None
    src: str | None = None
    stylesheet_name: str | None = None
    all_files: bool = False
    cache: Any = None


def html_dependency(name, version, src, stylesheet=None, all_files=True) -> HtmlDep:
    """R htmlDependency(): the stylesheet is read from src when it is named."""
    src = str(src)
    text = None
    if stylesheet is not None:
        with open(f"{src}/{stylesheet}", encoding="utf-8") as fh:
            text = "\n".join(fh.read().splitlines())
    return HtmlDep(name=name, version=version, kind="html", stylesheet=text,
                   src=src, stylesheet_name=stylesheet, all_files=all_files)


def r_chr(x: Any) -> str:
    """as.character() for a length-one R scalar."""
    if isinstance(x, bool):
        return "TRUE" if x else "FALSE"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if x.is_integer() and abs(x) < 1e15:
            return str(int(x))
        return format(x, ".15g")
    return str(x)


def trim_ws(x: str) -> str:
    return re.sub(r"^\s*", "", re.sub(r"\s*$", "", x))


def _strsplit_comma(s: str) -> list[str]:
    parts = s.split(",")
    if parts and parts[-1] == "" and s != "":
        parts = parts[:-1]
    return parts


def quote_css_font_families(values) -> str:
    """R quote_css_font_families(): quote names that need it and join with ", "."""
    if isinstance(values, str):
        values = [values]
    values = list(values)
    quoted = []
    for v in values:
        quoted += re.findall(r"'[^']*'", v) + re.findall(r'"[^"]*"', v)
    if any("," in q for q in quoted):
        text = ", ".join(values)
        warnings.warn(
            "`sass::font_collection()` doesn't automatically quote CSS `font-family` "
            "names when they contain a ','. If fonts don't render properly, make sure "
            f"family names are quoted properly: {text}",
            stacklevel=2,
        )
        return text
    pieces = [trim_ws(p) for v in values for p in _strsplit_comma(v)]
    out = []
    for p in pieces:
        needs_quote = re.search(r"[^A-Za-z-]", p) is not None
        has_quote = p.startswith("'") or p.startswith('"')
        out.append(f"'{p}'" if needs_quote and not has_quote else p)
    return ", ".join(out)


def font_dep_name(family: str) -> str:
    """R font_dep_name(): whitespace runs become underscores."""
    return re.sub(r"\s+", "_", trim_ws(family))


def url_encode(url: str) -> str:
    """R utils::URLencode(URL) with reserved = FALSE."""
    if re.search(r"%[0-9A-Fa-f]{2}", url):
        return url
    out = []
    for ch in url:
        if ch in _URL_KEEP:
            out.append(ch)
        else:
            out.append("".join(f"%{b:02X}" for b in ch.encode("utf-8")))
    return "".join(out)


def escape_attr(value: str) -> str:
    """htmltools::htmlEscape(attribute = TRUE)."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def link_head(href: str) -> str:
    """format(htmltools::tags$link(href = URLencode(href), rel = "stylesheet"))."""
    return f'<link href="{escape_attr(url_encode(href))}" rel="stylesheet"/>'


def font_face_css(props: list[tuple[str, str]]) -> str:
    """R font_face_css(): font properties get a font- prefix, src and unicode_range do not."""
    lines = []
    for name, value in props:
        prop = name if name in ("src", "unicode_range") else f"font-{name}"
        lines.append(f"  {prop}: {value};")
    return "@font-face {\n" + "\n".join(lines) + "\n}"


def match_arg(value, choices=DISPLAY_CHOICES) -> str:
    """R match.arg() for a single string, with R's partial matching."""
    choices = tuple(choices)
    if isinstance(value, (list, tuple)):
        if tuple(value) == choices:
            return choices[0]
        if len(value) != 1:
            raise ValueError("'arg' must be of length 1")
        value = value[0]
    if not isinstance(value, str):
        raise ValueError("'arg' must be NULL or a character vector")
    if value in choices:
        return value
    hits = [c for c in choices if value and c.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"'arg' should be one of {', '.join(choices)}")


def new_font_collection(families, html_deps, default_flag: bool = True, quote=True) -> FontCollection:
    """R new_font_collection(): quoting collapses the families into one string."""
    if quote is True:
        fam = [quote_css_font_families(list(families))]
    else:
        fam = list(families)
    return FontCollection(
        families=fam,
        html_deps=list(html_deps),
        default_flag=default_flag,
        quote=quote,
    )


def layers_of(bundle) -> list:
    """The layers of a sass bundle, whichever container the translation stored."""
    layers = bundle.layers
    return list(layers.values()) if isinstance(layers, dict) else list(layers)
