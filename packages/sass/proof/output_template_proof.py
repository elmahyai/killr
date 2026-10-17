"""Proof: sass::output_template() (R 0.4.10) against the Python translation."""

import os
import shutil

from _sass_proof_common import PROOF, run
from sass.output_template import output_template

tpl = str(PROOF / "outputs" / "output_template")


def no_suffix_shape():
    r = output_template(basename="out", dirname="dir", path=tpl)()
    result = {
        "parent_is_template": os.path.dirname(os.path.dirname(r)) == tpl,
        "dir_has_prefix": os.path.basename(os.path.dirname(r)).startswith("dir"),
        "file_name": os.path.basename(r),
    }
    shutil.rmtree(os.path.dirname(r), ignore_errors=True)
    return result


cases = {
    "suffix_css": lambda: output_template(basename="out", dirname="dir", path=tpl)(suffix="-s"),
    "suffix_min_css": lambda: output_template(basename="out", dirname="dir", path=tpl)(
        options={"output_style": 3}, suffix="-m"),
    "expanded_css": lambda: output_template(basename="out", dirname="dir", path=tpl)(
        options={"output_style": 1}, suffix="-e"),
    "fileext_given": lambda: output_template(basename="out", dirname="dir", fileext=".txt", path=tpl)(
        options={"output_style": 2}, suffix="-t"),
    "default_dirname": lambda: output_template(basename="page", path=tpl)(suffix="-d"),
    "no_suffix_shape": no_suffix_shape,
}

summary = run(
    "output_template",
    cases,
    timed=lambda: output_template(basename="out", dirname="dir", path=tpl)(suffix="-s"),
    primary="suffix_css",
)
