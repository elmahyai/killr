"""Python proof for getMargins(). Run from the repository root after getMargins_r.R:

    .venv/bin/python packages/hexbin/proof/getMargins_py.py

The inputs are the hexVP slots R wrote (mar in lines, plt in npc). Grid unit conversion is not
translated, so the check is the accessor's numeric result in the stored unit.
"""

from _proof_common import Report, hexvp_from_ref, load_ref, r_timing, time_median  # noqa: E402

from hexbin.getMargins import getMargins  # noqa: E402

NAME = "getMargins"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)
    hv = hexvp_from_ref(ref, "hv")
    hv2 = hexvp_from_ref(ref, "hv2")

    rep.num(ref, "case1", getMargins(hv, ret_unit="lines", numeric=True))
    rep.num(ref, "case2", getMargins(hv2, ret_unit="lines", numeric=True))

    def loop():
        for _ in range(2000):
            getMargins(hv, ret_unit="lines", numeric=True)

    py_median = time_median(loop)
    return rep.write(r_timing(ref), py_median, extra=["  timed call: 2000 calls per timing"])


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
