"""Proof: sass::is_font_collection() (R 0.4.10) against the Python translation."""

from _sass_proof_common import run
from sass.font_collection import font_collection
from sass.font_face import font_face
from sass.is_font_collection import is_font_collection
from sass.sass_bundle import sass_bundle

fc_obj = font_collection("Roboto")

cases = {
    "font_collection": lambda: is_font_collection(fc_obj),
    "font_face": lambda: is_font_collection(font_face("Open Sans", src="url(a.woff2)")),
    "string": lambda: is_font_collection("Roboto"),
    "null": lambda: is_font_collection(None),
    "bundle": lambda: is_font_collection(sass_bundle(a="x")),
    "plain_list": lambda: is_font_collection({"families": "x"}),
}

summary = run(
    "is_font_collection",
    cases,
    timed=lambda: is_font_collection(fc_obj),
    primary="font_collection",
)
