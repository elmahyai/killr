"""Summarize the gls and glsEstimate structure proofs from docs/output.

Reads docs/output/<name>-r.txt and docs/output/<name>-python.txt written by
proof/gls-compare.py, and writes docs/output/gls-standin-report.json with the
max abs diff per output group (coefficients, standard errors, sigma,
log-likelihood) and the timings. The gls rows use the nlminb STAND-IN
(nlme.gls._nlminb_standin), which is not a translation of PORT.

Usage: python3 gls-standin-report.py
"""

import json
from pathlib import Path

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
TOLERANCE = 1e-8

# gls rows: [coef (k), se (k), sigma, logLik]. glsEstimate rows are read as whole vectors.
GLS_CASES = ["gls-corAR1", "gls-corNatural", "gls-varPower"]
GLS_EST_CASES = ["glsEstimate-corNatural", "glsEstimate-varPower"]


def load(name: str, side: str) -> dict:
    return json.loads((OUTPUT / f"{name}-{side}.txt").read_text())


def gls_row(name: str) -> dict:
    r = load(name, "r")
    p = load(name, "python")
    rv, pv = r["value"], p["value"]
    k = (len(rv) - 2) // 2
    diff = [abs(a - b) for a, b in zip(rv, pv)]
    max_diff = max(diff)
    return {
        "case": name,
        "matches_1e-8": max_diff <= TOLERANCE,
        "max_abs_diff": max_diff,
        "max_abs_diff_coef": max(diff[:k]),
        "max_abs_diff_se": max(diff[k : 2 * k]),
        "max_abs_diff_sigma": diff[-2],
        "max_abs_diff_logLik": diff[-1],
        "r_ms": r["median_ms"],
        "translated_ms": p["median_ms"],
        "speedup": r["median_ms"] / p["median_ms"],
    }


def est_row(name: str) -> dict:
    r = load(name, "r")
    p = load(name, "python")
    max_diff = max(abs(a - b) for a, b in zip(r["value"], p["value"]))
    return {
        "case": name,
        "matches_1e-8": max_diff <= TOLERANCE,
        "max_abs_diff": max_diff,
        "r_ms": r["median_ms"],
        "translated_ms": p["median_ms"],
        "speedup": r["median_ms"] / p["median_ms"],
    }


def main() -> None:
    report = {
        "stand_in": "nlme.gls._nlminb_standin (scipy BFGS); NOT a translation of R PORT nlminb",
        "gls": [gls_row(name) for name in GLS_CASES],
        "glsEstimate": [est_row(name) for name in GLS_EST_CASES],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "gls-standin-report.json").write_text(json.dumps(report, indent=2) + "\n")
    for row in report["gls"] + report["glsEstimate"]:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
