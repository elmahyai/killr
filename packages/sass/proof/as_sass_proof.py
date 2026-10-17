"""Proof: sass::as_sass() (R 0.4.10) against the Python translation.

Each case compares the text and the html dependencies, as R's
html_dependencies attribute. The local = TRUE font is rendered from the
offline fixture cache (fixtures/google_local), so no network is used.
"""

from _sass_dep_common import as_html_case, google_cache, proof_fixture
from _sass_proof_common import run
from sass._common import SassLayer
from sass._sass_values import html_dependency
from sass.as_sass import as_sass
from sass.font_collection import font_collection
from sass.font_google import font_google
from sass.sass_bundle import sass_bundle
from sass.sass_layer import sass_layer


class Unsupported:
    """A Python object with no as_sass() method, like the R zzz class."""


CACHE = google_cache()
bundle_input = sass_bundle(a={"x": 1}, b="p{q:r}")

cases = {
    "string": lambda: as_html_case(as_sass("a{b:c}")),
    "character_vector": lambda: as_html_case(as_sass((".a{", "  b: c", "}"))),
    "null": lambda: as_html_case(as_sass(None)),
    "numeric": lambda: as_html_case(as_sass(3.5)),
    "integer_valued": lambda: as_html_case(as_sass(12)),
    "logical": lambda: as_html_case(as_sass(True)),
    "named_list": lambda: as_html_case(as_sass({"x": 1, "y": "red"})),
    "layer": lambda: as_html_case(as_sass(SassLayer(defaults={"x": 1}, rules="a{b:c}"))),
    "bundle": lambda: as_html_case(as_sass(bundle_input)),
    "font_collection": lambda: as_html_case(as_sass(font_collection("Open Sans"))),
    "google_local_default": lambda: as_html_case(as_sass([
        {"font-variable": font_google("Roboto", cache=CACHE)},
        "body{font-family: $font-variable}",
    ])),
    "google_link": lambda: as_html_case(as_sass(font_google("Roboto", local=False, cache=None))),
    "bundle_font": lambda: as_html_case(as_sass(sass_bundle(
        a={"font-variable": font_google("Roboto", cache=CACHE)}
    ))),
    "layer_html_dep": lambda: as_html_case(as_sass(sass_layer(
        html_deps=html_dependency("zz", "1.0", src=proof_fixture("dep_src"), stylesheet="zz.css"),
        rules="a{b:c}",
    ))),
    "unsupported_class": lambda: as_html_case(as_sass(Unsupported())),
}

summary = run(
    "as_sass",
    cases,
    timed=lambda: as_sass(bundle_input),
    primary="bundle",
)
