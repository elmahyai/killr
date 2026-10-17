"""Proof: prettyunits.rounding.pretty_signif against the R prettyunits 1.2.0 result."""

from harness import run_proof

from prettyunits.rounding import pretty_signif

NAN = float("nan")
INF = float("inf")
X = [0.0, 123456.789, 0.000123456, 1e-7, 9.9999, 99.9999, 999999.5, -0.0004,
     1234567.0, None, NAN, INF, -INF, 0.1 + 0.2, 5e-324, -0.0]


def one():
    return {
        "default": pretty_signif(X),
        "d2": pretty_signif(X, digits=2),
        "d3_inf": pretty_signif(X, digits=3, sci_range=float("inf")),
        "d4_sci0": pretty_signif(X, digits=4, sci_range=0, sci_sep="x10^"),
        "vec": pretty_signif([0.99999, 9.9999e-5], digits=3),
    }


run_proof("pretty_signif", one)
