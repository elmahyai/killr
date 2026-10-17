"""Python proof for getYscale(). Run from the repository root after getYscale_r.R:

    .venv/bin/python packages/hexbin/proof/getYscale_py.py

The R generic is commented out in hexbin 1.28.6; the reference is its body, `x@yscale`. The
inputs are the hexVP slots R wrote.
"""

from _proof_common import Report, hexvp_from_ref, load_ref, r_timing, time_median  # noqa: E402

from hexbin.getYscale import getYscale  # noqa: E402

NAME = "getYscale"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)
    hv = hexvp_from_ref(ref, "hv")
    hv2 = hexvp_from_ref(ref, "hv2")

    rep.num(ref, "case1", getYscale(hv))
    rep.num(ref, "case2", getYscale(hv2))

    def loop():
        for _ in range(2000):
            getYscale(hv)

    py_median = time_median(loop)
    return rep.write(r_timing(ref), py_median, extra=["  timed call: 2000 calls per timing"])


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
