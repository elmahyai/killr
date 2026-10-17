"""Proof: lscv against R locfit 1.5-9.12.

Blocked: the default lscv runs locfit.raw with geth = 6 (dens_lscv, the density
LSCV path), which crates/locfit does not contain. This script records the reason.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.lscv import lscv  # noqa: E402


def main():
    d = L.inputs()
    try:
        lscv(d["dsamp"])
        L.blocked("lscv", "unexpected: ran without dens_lscv")
        sys.exit(1)
    except NotImplementedError as exc:
        L.blocked("lscv", f"dens_lscv (geth = 6) in crates/locfit: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
