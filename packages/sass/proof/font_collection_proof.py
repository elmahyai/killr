"""Proof: sass::font_collection() (R 0.4.10) against the Python translation.

Mixed positional and named fonts keep R's order through Named(name, value).
The local = TRUE font is rendered from the offline fixture cache, so no
network is used.
"""

from _sass_dep_common import canon_collection, google_cache
from _sass_proof_common import run
from sass.font_collection import Named, font_collection

CACHE = google_cache()

cases = {
    "plain": lambda: canon_collection(font_collection("Roboto")),
    "two_families_quoted": lambda: canon_collection(font_collection("Open Sans", "serif", default_flag=False)),
    "quote_false": lambda: canon_collection(font_collection("Open Sans", "serif", quote=False)),
    "face": lambda: canon_collection(font_collection(face={"family": "Open Sans", "src": "url(a.woff2)", "weight": 400})),
    "link": lambda: canon_collection(font_collection(link={"family": "Lato", "href": "https://example.com/lato.css"})),
    "google_link": lambda: canon_collection(font_collection(google={"family": "Roboto", "local": False,
                                                                     "cache": None, "wght": (400, 700)})),
    "google_local_default": lambda: canon_collection(font_collection(google={"family": "Roboto", "local": True,
                                                                             "cache": CACHE})),
    "collection_nested": lambda: canon_collection(font_collection(collection=("Roboto", "serif"))),
    "mixed_order_link": lambda: canon_collection(font_collection(
        "Open Sans", Named("google", {"family": "Roboto", "local": False, "cache": None}), "serif")),
    "mixed_order_local": lambda: canon_collection(font_collection(
        "Open Sans", Named("google", {"family": "Roboto", "local": True, "cache": CACHE}), "serif",
        default_flag=False)),
    "unsupported_name": lambda: canon_collection(font_collection(bogus=("x",))),
    "non_string": lambda: canon_collection(font_collection(1)),
}

summary = run(
    "font_collection",
    cases,
    timed=lambda: font_collection("Open Sans", "serif", default_flag=False),
    primary="two_families_quoted",
)
