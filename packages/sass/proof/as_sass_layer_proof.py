"""Proof: sass::as_sass_layer() (R 0.4.10) against the Python translation."""

from _sass_proof_common import run
from sass._common import SassLayer
from sass.as_sass_layer import as_sass_layer
from sass.sass_bundle import sass_bundle

bundle_input = sass_bundle(a={"x": 1}, b="p{q:r}")

cases = {
    "layer_input": lambda: as_sass_layer(SassLayer(rules="a{b:c}")),
    "character": lambda: as_sass_layer("a{b:c}"),
    "numeric": lambda: as_sass_layer(1),
    "named_list": lambda: as_sass_layer({"x": 1}),
    "unnamed_list": lambda: as_sass_layer(["a{}", "b{}"]),
    "bundle_two_defaults": lambda: as_sass_layer(sass_bundle(a={"x": 1}, b={"x": 2})),
    "bundle_mixed": lambda: as_sass_layer(bundle_input),
    "null": lambda: as_sass_layer(None),
}

summary = run(
    "as_sass_layer",
    cases,
    timed=lambda: as_sass_layer(bundle_input),
    primary="bundle_mixed",
)
