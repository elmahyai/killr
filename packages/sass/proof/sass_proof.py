"""Proof: sass::sass() (R 0.4.10) against the Python translation.

Compiles through the libsass wrapper (sass_kernel). Every call is a fresh
compile on both sides; R uses cache = FALSE.
"""

from pathlib import Path

from _sass_proof_common import OUTPUTS, PROOF, run
from sass.sass import sass

out_file = OUTPUTS / "sass_output.css"


def output_file_case():
    returned = sass("a{b:c}", output=str(out_file))
    return {
        "returned": Path(returned).name,
        "file": out_file.read_bytes().decode("utf-8"),
    }


cases = {
    "string": lambda: sass("a{b:c}"),
    "named_defaults": lambda: sass({"x": "1px", "": "a{b:$x}"}),
    "compressed": lambda: sass("a{b:c}", options={"output_style": "compressed"}),
    "nested_indent4": lambda: sass(".a { b: c; .d { e: f } }",
                                   options={"output_style": "nested", "indent_width": 4}),
    "compact": lambda: sass(".a { b: c; .d { e: f } }", options={"output_style": "compact"}),
    "nested_tab": lambda: sass(".a { b: c; .d { e: f } }",
                               options={"output_style": "nested", "indent_type": "tab"}),
    "precision2": lambda: sass("a{b: 1px / 3}", options={"precision": 2}),
    "indented_syntax": lambda: sass("a\n  b: c", options={"indented_syntax": True}),
    "output_file": output_file_case,
    "null_input": lambda: sass(None),
    "bad_style": lambda: sass("a{b:c}", options={"output_style": "x"}),
}

primary_css = sass({"x": "1px", "": "a{b:$x}"})

summary = run(
    "sass",
    cases,
    timed=lambda: sass({"x": "1px", "": "a{b:$x}"}),
    primary="named_defaults",
    text_extra={"primary CSS (named_defaults), Python": primary_css},
)
