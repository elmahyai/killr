"""Proof: lscv.exact against R locfit 1.5-9.12.

Blocked: R calls the C routine slscv (kdecri, exact density LSCV), which
crates/locfit does not contain. This script records the reason.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.lscv_exact import lscv_exact  # noqa: E402


def main():
    d = L.inputs()
    try:
        lscv_exact(d["dsamp"], h=0.3)
        L.blocked("lscv_exact", "unexpected: ran without slscv")
        sys.exit(1)
    except NotImplementedError as exc:
        L.blocked("lscv_exact", f"slscv (kdecri) in crates/locfit: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
