"""Proof: sass::font_face() (R 0.4.10) against the Python translation."""

from _sass_proof_common import run
from sass.font_face import font_face

cases = {
    "basic": lambda: font_face("Open Sans", src="url(a.woff2)", weight=400, style="normal"),
    "vectors": lambda: font_face(
        ("Roboto", "Helvetica Neue"),
        src=("url(a.woff2)", "url(b.woff)"),
        unicode_range=("U+0000-00FF", "U+0131"),
        display="block",
        stretch="condensed",
        variant="small-caps",
    ),
    "no_display": lambda: font_face("Foo", src="url(f.woff2)", display=None),
    "partial_display": lambda: font_face("Foo", src="url(f.woff2)", display="sw"),
    "bad_display": lambda: font_face("Foo", src="url(f.woff2)", display="nope"),
}

summary = run(
    "font_face",
    cases,
    timed=lambda: font_face(
        ("Roboto", "Helvetica Neue"),
        src=("url(a.woff2)", "url(b.woff)"),
        unicode_range=("U+0000-00FF", "U+0131"),
        display="block",
        stretch="condensed",
        variant="small-caps",
    ),
    primary="vectors",
)
