"""recalc proof for the 13 nlme classes: Python against R 3.1-171.

Runs proof/recalc-r.R, runs the same 13 cases here, writes both outputs under
docs/output/, and prints the comparison (max_abs_diff, r_ms, translated_ms, speedup).
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
from coverage_common import ROOT, load_nlme  # noqa: E402

load_nlme()
from nlme.corar1 import corAR1  # noqa: E402
from nlme.corcar1 import corCAR1  # noqa: E402
from nlme.corexp import corExp  # noqa: E402
from nlme.corgaus import corGaus  # noqa: E402
from nlme.corlin import corLin  # noqa: E402
from nlme.corratio import corRatio  # noqa: E402
from nlme.corspatial import corSpatial  # noqa: E402
from nlme.corspher import corSpher  # noqa: E402
from nlme.corsymm import corSymm  # noqa: E402
from nlme.glsapvar import ConLin  # noqa: E402
from nlme.initialize import Initialize  # noqa: E402
from nlme.pdcompsymm import pdCompSymm  # noqa: E402
from nlme.recalc import recalc  # noqa: E402
from nlme.restruct import _default_settings, _finalize_restruct, load_pixel_csv, reStruct  # noqa: E402

OUT = ROOT / "docs" / "output"
TOL = 1e-8

# The Pixel conLin lme() passes to Initialize.reStruct (written by reStruct-conlin-capture-r.R).
_FIXTURE = json.loads((ROOT / "proof" / "data" / "reStruct-pixel-conlin.json").read_text())
PIXEL_N = int(_FIXTURE["N"])
PIXEL_NCOL = int(_FIXTURE["ncol"])
PIXEL_XY = np.asarray(_FIXTURE["Xy"], dtype=np.float64).reshape(PIXEL_N, PIXEL_NCOL, order="F")
PIXEL_DIMS = _FIXTURE["dims"]
PIXEL_SIGMA = float(_FIXTURE["sigma"])
PIXEL = load_pixel_csv()

DAT_SUB = {"Subject": ["a", "a", "a", "a", "b", "b", "b"], "t": [1, 2, 3, 4, 1, 2, 4]}
DAT_AR = {"Subject": ["a", "a", "a", "b", "b", "b", "b"], "t": [1, 2, 4, 1, 2, 3, 5]}
DAT_XY = {
    "Subject": ["a", "a", "a", "a", "b", "b", "b"],
    "x": [0.0, 1.0, 0.5, 2.0, 0.2, 1.4, 2.6],
    "y": [0.0, 0.0, 1.0, 0.5, 0.3, 1.1, 0.4],
}


def con(logLik: float = 0.5) -> ConLin:
    return ConLin(
        Xy=np.arange(1, 15, dtype=np.float64).reshape(7, 2, order="F"),
        dims={"N": 7, "p": 2},
        logLik=logLik,
    )


def pixel_conlin(logLik: float = 0.0) -> ConLin:
    return ConLin(Xy=PIXEL_XY.copy(), dims=PIXEL_DIMS, logLik=logLik, sigma=PIXEL_SIGMA)


def pixel_rs(pd_class: str):
    return Initialize(
        reStruct({"Dog": "~day", "Side": "~1"}, pdClass=pd_class, data=PIXEL),
        PIXEL,
        conLin=pixel_conlin(),
    )


def pdcomp_rs():
    # Already-initialized blocks, as in the R proof (no EM step).
    template_dog = reStruct({"Dog": "~day"}, pdClass="pdCompSymm", data=PIXEL).blocks[0][1]
    template_side = reStruct({"Side": "~1"}, data=PIXEL).blocks[0][1]
    dog_values = np.asarray(
        pdCompSymm(np.array([[2.0, 0.6], [0.6, 2.0]]), form="~ day", data=PIXEL).values,
        dtype=np.float64,
    )
    dog = replace(template_dog, values=dog_values)
    side = replace(template_side, values=np.array([np.log(2.0)], dtype=np.float64))
    blocks = [("Side", side), ("Dog", dog)]
    return _finalize_restruct(blocks, _default_settings(False, [dog, side]), None)


def pair(obj, conlin):
    return (obj, conlin)


# One setup per class, mirroring cases in recalc-r.R (built outside the timer).
CASES = {
    "corSymm": lambda: [
        pair(Initialize(corSymm([0.3, 0.1, 0.2, 0.05, 0.1, 0.25], form="~ t | Subject"), DAT_SUB), con()),
        pair(Initialize(corSymm(form="~ t | Subject"), DAT_SUB), con()),
    ],
    "corAR1": lambda: [
        pair(Initialize(corAR1(0.3, form="~ t | Subject"), DAT_AR), con()),
        pair(Initialize(corAR1(-0.4, form="~ t | Subject"), DAT_AR), con()),
    ],
    "pdSymm": lambda: [pair(pixel_rs("pdSymm"), pixel_conlin(0.5))],
    "pdDiag": lambda: [pair(pixel_rs("pdDiag"), pixel_conlin(0.5))],
    "pdIdent": lambda: [pair(pixel_rs("pdIdent"), pixel_conlin(0.5))],
    "pdCompSymm": lambda: [pair(pdcomp_rs(), pixel_conlin(0.5))],
    "corLin": lambda: [
        pair(Initialize(corLin(3, form="~ x + y | Subject"), DAT_XY), con()),
        pair(Initialize(corLin([3, 0.2], form="~ x + y | Subject", nugget=True, metric="man"), DAT_XY), con()),
    ],
    "corRatio": lambda: [
        pair(Initialize(corRatio(3, form="~ x + y | Subject"), DAT_XY), con()),
        pair(Initialize(corRatio([3, 0.2], form="~ x + y | Subject", nugget=True, metric="man"), DAT_XY), con()),
    ],
    "corSpher": lambda: [
        pair(Initialize(corSpher(3, form="~ x + y | Subject"), DAT_XY), con()),
        pair(Initialize(corSpher([3, 0.2], form="~ x + y | Subject", nugget=True, metric="man"), DAT_XY), con()),
    ],
    "corExp": lambda: [
        pair(Initialize(corExp(3, form="~ x + y | Subject"), DAT_XY), con()),
        pair(Initialize(corExp([3, 0.2], form="~ x + y | Subject", nugget=True, metric="man"), DAT_XY), con()),
    ],
    "corGaus": lambda: [
        pair(Initialize(corGaus(3, form="~ x + y | Subject"), DAT_XY), con()),
        pair(Initialize(corGaus([3, 0.2], form="~ x + y | Subject", nugget=True, metric="man"), DAT_XY), con()),
    ],
    "corSpatial": lambda: [
        pair(Initialize(corSpatial(3, form="~ x + y | Subject", type="spherical"), DAT_XY), con()),
        pair(
            Initialize(
                corSpatial([3, 0.2], form="~ x + y | Subject", nugget=True, type="exponential", metric="man"),
                DAT_XY,
            ),
            con(),
        ),
    ],
    "corCAR1": lambda: [
        pair(Initialize(corCAR1(0.2, form="~ t | Subject"), DAT_SUB), con()),
        pair(Initialize(corCAR1(0.7, form="~ t | Subject"), DAT_SUB), con()),
    ],
}


def run_pairs(pairs) -> np.ndarray:
    parts = []
    for obj, conlin in pairs:
        result = recalc(obj, conlin)
        parts.append(np.ravel(np.asarray(result.Xy, dtype=np.float64), order="F"))
        parts.append(np.asarray([float(result.logLik)], dtype=np.float64))
    return np.concatenate(parts)


def timed(pairs) -> dict:
    """One untimed recalc, then the median of 20 timed recalc calls (milliseconds)."""
    value = run_pairs(pairs)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        run_pairs(pairs)
        elapsed.append((time.perf_counter() - started) * 1000)
    return {"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}


def python_results() -> dict:
    return {name: timed(setup()) for name, setup in CASES.items()}


def r_results() -> dict:
    command = ["Rscript", str(PROOF / "recalc-r.R")]
    done = subprocess.run(command, capture_output=True, text=True, check=True)
    # R may print tracing messages before the JSON line; the JSON is the last line.
    json_lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    return json.loads(json_lines[-1])


def compare(r_entry: dict, py_entry: dict) -> tuple[str, float, float, float]:
    r_vals = np.asarray(r_entry["value"], dtype=np.float64)
    py_vals = np.asarray(py_entry["value"], dtype=np.float64)
    if r_vals.shape != py_vals.shape:
        return "no", float("nan"), r_entry["median_ms"], py_entry["median_ms"]
    max_diff = float(np.max(np.abs(r_vals - py_vals)))
    ok = "yes" if max_diff <= TOL else "no"
    return ok, max_diff, float(r_entry["median_ms"]), float(py_entry["median_ms"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    r_out = r_results()
    py_out = python_results()
    (OUT / "recalc-r.txt").write_text(json.dumps(r_out) + "\n")
    (OUT / "recalc-python.txt").write_text(json.dumps(py_out) + "\n")
    lines = [
        "class | matches (<=1e-8) | max_abs_diff | r_ms | translated_ms | speedup (R/Python)",
    ]
    for name in CASES:
        ok, diff, r_ms, py_ms = compare(r_out[name], py_out[name])
        speed = r_ms / py_ms if py_ms > 0 else float("inf")
        lines.append(f"{name} | {ok} | {diff:.3g} | {r_ms:.4g} | {py_ms:.4g} | {speed:.3g}")
    summary = "\n".join(lines) + "\n"
    (OUT / "recalc-compare.txt").write_text(summary)
    print(summary, end="")


if __name__ == "__main__":
    main()
