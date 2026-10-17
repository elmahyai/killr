"""Proof: sass::is_sass_bundle() (R 0.4.10) against the Python translation."""

from _sass_proof_common import run
from sass._common import SassLayer
from sass.font_collection import font_collection
from sass.is_sass_bundle import is_sass_bundle
from sass.sass_bundle import sass_bundle

bundle_obj = sass_bundle(a="x")

cases = {
    "bundle": lambda: is_sass_bundle(bundle_obj),
    "bundle_rules_arg": lambda: is_sass_bundle(sass_bundle(rules="x")),
    "layer_struct": lambda: is_sass_bundle(SassLayer(rules="x")),
    "string": lambda: is_sass_bundle("x"),
    "null": lambda: is_sass_bundle(None),
    "plain_list": lambda: is_sass_bundle({"layers": []}),
    "font_collection": lambda: is_sass_bundle(font_collection("Roboto")),
}

summary = run(
    "is_sass_bundle",
    cases,
    timed=lambda: is_sass_bundle(bundle_obj),
    primary="bundle",
)
