"""Proof: prettyunits.rounding.pretty_round against the R prettyunits 1.2.0 result.

In R 4.5 a scalar digits argument with two or more values in scientific
notation fails inside formatC. The Python port raises in the same case, so
those whole-vector calls are wrapped in try_val on both sides.
"""

from harness import run_proof, try_val

from prettyunits.rounding import pretty_round

NAN = float("nan")
INF = float("inf")
X = [123.05, 1234567.0, None, NAN, INF, -INF, -0.0001, 0.0, 2.5, 3.5, -2.675,
     0.1234567, 99.999, 1e-7, 6.02e23, -0.4]


def one():
    return {
        "d3_sci5": try_val(pretty_round, X, digits=3, sci_range=5),
        "d3_sci5_each": [pretty_round(v, digits=3, sci_range=5) for v in X],
        "d0": pretty_round(X),
        "d_neg2": pretty_round(X, digits=-2),
        "sci0_x10": try_val(pretty_round, X, digits=2, sci_range=0, sci_sep="x10^"),
        "sci0_x10_each": [pretty_round(v, digits=2, sci_range=0, sci_sep="x10^") for v in X],
        "vec_digits": pretty_round([1.23456, 2.5, 1234.5678], digits=[2, 0, 1]),
        "scalar": pretty_round(3.14159, 2),
        "one_sci": pretty_round(1234567.0, digits=3, sci_range=5),
        "neg_zero": pretty_round([-0.0001, -0.4], digits=0),
        "bad_digits": try_val(pretty_round, [1.0, 2.0, 3.0], digits=[1, 2]),
    }


run_proof("pretty_round", one)
