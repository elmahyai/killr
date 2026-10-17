"""Python proof for LinGray(). Run from the repository root after LinGray_r.R:

    .venv/bin/python packages/hexbin/proof/LinGray_py.py
"""

from _proof_common import Report, load_ref, r_timing, time_median  # noqa: E402

from hexbin.LinGray import LinGray  # noqa: E402

NAME = "LinGray"


def _text(f) -> str:
    try:
        return " ".join(f())
    except ValueError:
        return "error"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)

    rep.text(ref, "case1", _text(lambda: LinGray(20)))
    rep.text(ref, "case2", _text(lambda: LinGray(7, beg=90, end=15)))
    rep.text(ref, "case3", _text(lambda: LinGray(1)))
    rep.text(ref, "case4", _text(lambda: LinGray(300, beg=1, end=92)))
    rep.text(ref, "case5", _text(lambda: LinGray(5, beg=1, end=256)))

    py_median = time_median(lambda: LinGray(2000))
    return rep.write(r_timing(ref), py_median, extra=["  timed call: LinGray(2000)", "  table formatted once at import; the R call rebuilds its table each time"])


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
