"""Translation of sass::font_google().

The Google Fonts href is built here. With local = TRUE (the default), the
dependency is returned unrendered, as R's tagFunction is, and
render_google_local() builds it when it is needed:

1. The stylesheet is read from the cache under the href. A hit is the
   localized CSS that an earlier run stored.
2. Every url(...) in that stylesheet names a font file. Each file is read from
   the cache under its basename.
3. The stylesheet and the font files are written to a new directory, and the
   dependency reads from that directory, as R's font_dep_google_local does.

The cache is any object with get_file(key, outfile) and set_file(key, file),
as R's sass_file_cache is. Keys are the href for the stylesheet and the font
file basename for each font. R keys its cache with rlang hashes, which this
translation does not reproduce. The cache contents are the same either way.

A cache miss means R would download the stylesheet or a font file. That
download is not translated, so render_google_local raises NetworkRequired. With
local = FALSE, the dependency is a stylesheet link and nothing is fetched.
"""

import os
import re
import tempfile
from pathlib import Path

from ._sass_values import (
    DISPLAY_CHOICES,
    SASS_VERSION,
    HtmlDep,
    font_dep_name,
    link_head,
    match_arg,
    new_font_collection,
    r_chr,
)

_URL_RE = re.compile(r"url\(([^)]+)")


class NetworkRequired(RuntimeError):
    """The render needs a download that this translation does not perform."""


class _NoCache:
    """R resolve_cache(NULL): every lookup misses."""

    def get_file(self, key, outfile, overwrite=True):
        return False

    def set_file(self, key, file):
        return False


def _resolve_cache(cache):
    if cache is not None and callable(getattr(cache, "get_file", None)) \
            and callable(getattr(cache, "set_file", None)):
        return cache
    return _NoCache()


def _as_vector(x):
    return list(x) if isinstance(x, (list, tuple)) else [x]


def font_google(family, local=True, cache=None, wght=None, ital=None, display=DISPLAY_CHOICES):
    if not isinstance(family, str):
        raise TypeError("Font `family` definitions must be a character string (length 1).")
    if not isinstance(local, bool):
        raise TypeError("local must be logical")
    if wght is not None:
        wght_values = _as_vector(wght)
        if not all(isinstance(w, (int, float, str)) and not isinstance(w, bool) for w in wght_values):
            raise TypeError("wght must be character or numeric")
        wght = sorted(wght_values)
    if ital is not None:
        ital_values = _as_vector(ital)
        if not all(v in (0, 1) for v in ital_values):
            raise ValueError("ital must contain only 0 or 1")
        ital = sorted(ital_values)
    display = match_arg(display, DISPLAY_CHOICES)

    if wght is None and ital is None:
        axis = ""
    elif ital is None:
        axis = ":wght@" + ";".join(r_chr(w) for w in wght)
    elif wght is None:
        axis = ":ital@" + ";".join(r_chr(i) for i in ital)
    else:
        pairs = [f"{r_chr(i)},{r_chr(w)}" for i in ital for w in wght]
        axis = ":ital,wght@" + ";".join(pairs)

    href = f"https://fonts.googleapis.com/css2?family={family}{axis}&display={display}"
    if local:
        dep = HtmlDep(name=font_dep_name(family), version=SASS_VERSION,
                      kind="google_local", href=href, cache=cache)
    else:
        dep = HtmlDep(name=font_dep_name(family), version=SASS_VERSION,
                      kind="link", href=href, head=link_head(href))
    return new_font_collection([family], [dep])


def render_google_local(dep: HtmlDep) -> HtmlDep:
    """R font_dep_google_local(): build the local stylesheet and font files.

    Returns a new dependency with the stylesheet text, the directory that holds
    font.css and the font files, and all_files set, as htmltools does.
    """
    cache = _resolve_cache(dep.cache)
    tmpdir = tempfile.mkdtemp(prefix="sass-google-")
    css_file = os.path.join(tmpdir, "font.css")

    if not cache.get_file(dep.href, css_file):
        raise NetworkRequired(
            f"font_google('{dep.name}') needs the Google Fonts stylesheet at {dep.href}. "
            "It is not in the cache, and the download is not translated."
        )
    lines = Path(css_file).read_text(encoding="utf-8").splitlines()

    for line in lines:
        match = _URL_RE.search(line)
        if match is None:
            continue
        url = match.group(1)
        basename = os.path.basename(url)
        font_file = os.path.join(tmpdir, basename)
        if cache.get_file(basename, font_file):
            continue
        raise NetworkRequired(
            f"font_google('{dep.name}') needs the font file {basename}. "
            "It is not in the cache, and the download is not translated."
        )

    return HtmlDep(
        name=dep.name,
        version=dep.version,
        kind="google_local",
        href=dep.href,
        stylesheet="\n".join(lines),
        src=tmpdir,
        stylesheet_name="font.css",
        all_files=True,
    )
