"""Proof: sass::font_google() (R 0.4.10) against the Python translation.

The default local = TRUE path is run. It renders the stylesheet and the font
file from the offline fixture cache (fixtures/google_local), the same files R
reads, so no network is used. The primary timed call is that default path:
construct the font, then render its html dependency.
"""

from _sass_dep_common import canon_collection, google_cache
from _sass_proof_common import run
from sass.font_google import font_google, render_google_local

CACHE = google_cache()

cases = {
    "plain_link": lambda: canon_collection(font_google("Roboto", local=False, cache=None)),
    "axes_wght_ital": lambda: canon_collection(font_google("Roboto", local=False, cache=None,
                                                           wght=(700, 400), ital=(1, 0))),
    "wght_only_block": lambda: canon_collection(font_google("Open Sans", local=False, cache=None,
                                                            wght=(300, 400), display="block")),
    "ital_only": lambda: canon_collection(font_google("Lato", local=False, cache=None, ital=1)),
    "local_default": lambda: canon_collection(font_google("Roboto", cache=CACHE)),
    "bad_local": lambda: canon_collection(font_google("Roboto", local="yes", cache=None)),
    "bad_ital": lambda: canon_collection(font_google("Roboto", local=False, cache=None, ital=2)),
}

summary = run(
    "font_google",
    cases,
    timed=lambda: render_google_local(font_google("Roboto", cache=CACHE).html_deps[0]),
    primary="local_default",
)
