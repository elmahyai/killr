"""Python proof for getXscale(). Run from the repository root after getXscale_r.R:

    .venv/bin/python packages/hexbin/proof/getXscale_py.py

The R generic is commented out in hexbin 1.28.6; the reference is its body, `x@xscale`. The
inputs are the hexVP slots R wrote.
"""

from _proof_common import Report, hexvp_from_ref, load_ref, r_timing, time_median  # noqa: E402

from hexbin.getXscale import getXscale  # noqa: E402

NAME = "getXscale"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)
    hv = hexvp_from_ref(ref, "hv")
    hv2 = hexvp_from_ref(ref, "hv2")

    rep.num(ref, "case1", getXscale(hv))
    rep.num(ref, "case2", getXscale(hv2))

    def loop():
        for _ in range(2000):
            getXscale(hv)

    py_median = time_median(loop)
    return rep.write(r_timing(ref), py_median, extra=["  timed call: 2000 calls per timing"])


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
