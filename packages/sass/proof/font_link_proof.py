"""Proof: sass::font_link() (R 0.4.10) against the Python translation."""

from _sass_proof_common import run
from sass.font_link import font_link

cases = {
    "plain": lambda: font_link("Open Sans", "https://fonts.example.com/css2?family=Open+Sans&display=swap"),
    "escaped": lambda: font_link("Lato", "https://example.com/a b.css?x='1'&y=2"),
    "bad_family": lambda: font_link(("A", "B"), "https://example.com/x.css"),
}

summary = run(
    "font_link",
    cases,
    timed=lambda: font_link("Open Sans", "https://fonts.example.com/css2?family=Open+Sans&display=swap"),
    primary="plain",
)
