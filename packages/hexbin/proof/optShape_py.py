"""Python proof for optShape(). Run from the repository root after optShape_r.R:

    .venv/bin/python packages/hexbin/proof/optShape_py.py

The timed call is a loop of 2000 calls, as in optShape_r.R, because one call is below the
clock resolution. The reported medians are for the 2000-call loop on both sides.
"""

from _proof_common import Report, hexvp_from_ref, load_ref, r_timing, time_median  # noqa: E402

from hexbin.optShape import optShape  # noqa: E402

NAME = "optShape"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)

    rep.num(ref, "case1", optShape(height=6, width=4))
    rep.num(ref, "case2", optShape(height=6, width=4, mar=(1, 0.5, 1, 0.5)))
    rep.num(ref, "case3", optShape(height=2.5, width=7, mar=(0.2, 0.3, 0.4, 0.5)))
    rep.num(ref, "case4", optShape(height=1, width=3))
    rep.num(ref, "case5", optShape(hexvp_from_ref(ref, "opt.hv")))

    def loop():
        for _ in range(2000):
            optShape(height=6, width=4, mar=(1, 0.5, 1, 0.5))

    py_median = time_median(loop)
    return rep.write(r_timing(ref), py_median, extra=["  timed call: 2000 calls per timing"])


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
