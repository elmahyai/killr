"""Python proof for BTY(). Run from the repository root after BTY_r.R:

    .venv/bin/python packages/hexbin/proof/BTY_py.py
"""

from _proof_common import Report, load_ref, r_timing, time_median  # noqa: E402

from hexbin.BTY import BTY  # noqa: E402

NAME = "BTY"


def _text(f) -> str:
    try:
        return " ".join(f())
    except ValueError:
        return "error"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)

    rep.text(ref, "case1", _text(lambda: BTY(10)))
    rep.text(ref, "case2", _text(lambda: BTY(7, beg=20, end=200)))
    rep.text(ref, "case3", _text(lambda: BTY(1)))
    rep.text(ref, "case4", _text(lambda: BTY(300, beg=1, end=256)))

    py_median = time_median(lambda: BTY(2000))
    return rep.write(r_timing(ref), py_median, extra=["  timed call: BTY(2000)", "  table formatted once at import; the R call rebuilds its table each time"])


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
