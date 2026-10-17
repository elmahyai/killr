"""Python proof for locfit::rbox against the R reference (locfit 1.5-9.12).

Run from the repository root after rbox_r.R:
    python3 packages/locfit/proof/rbox_python.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locfit_proof_common import (check_case, load, new_state, read_fixture,  # noqa: E402
                                 read_r_output, read_r_timing, report, time_py_ms,
                                 to_plain, write_python_output)


def main() -> None:
    rbox = load("rbox").rbox
    cases = read_fixture("rbox")["cases"]
    r_cases = read_r_output("rbox")["cases"]
    total, lines, py_out = new_state(), [], {}
    for name, args in cases.items():
        kwargs = args if isinstance(args, dict) else {}
        try:
            value = to_plain(rbox(**kwargs))
        except ValueError as exc:
            value = {"error": True, "message": str(exc)}
        py_out[name] = value
        check_case(name, r_cases[name], value, total, lines)
    write_python_output("rbox", py_out)

    primary = cases["kdtree"]
    py_ms = time_py_ms(lambda: rbox(**primary))
    r_ms = read_r_timing("rbox")
    print(report("rbox", lines, total, r_ms, py_ms))


if __name__ == "__main__":
    main()
