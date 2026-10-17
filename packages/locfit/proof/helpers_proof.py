"""Fixed-input R/Python proofs for the translated locfit helpers.

Run from the repository root with ``LOCFIT_RLIB`` pointing at locfit 1.5-9.12.
The script writes one R value file, one translated value file, and one timing
summary for each helper that can be evaluated without a pending package port.
"""

import statistics
import subprocess
import time
from pathlib import Path
import importlib.util
import numpy as np

ROOT = Path(__file__).parents[3]
OUT = ROOT / "packages/locfit/docs/output"
OUT.mkdir(parents=True, exist_ok=True)
R = "library(locfit,lib.loc=Sys.getenv('LOCFIT_RLIB')); x<-seq(-1,1,length.out=20); y<-seq(1,20); writeLines(capture.output(dput(list(rbox(),xbar(),sjpi(x,c(.5,.8)),spence.15(y),spence.21(y)))), 'locfit_helpers_r.txt')"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "packages/locfit" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def timed(fn):
    fn()
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples) * 1000.0


def main():
    subprocess.run(["Rscript", "--vanilla", "-e", R], cwd=ROOT, check=True)
    results = {}
    cases = {
        "rbox": lambda: load("rbox").rbox(),
        "xbar": lambda: load("xbar").xbar(),
        "sjpi": lambda: load("sjpi").sjpi(np.linspace(-1, 1, 20), [.5, .8]),
        "spence.15": lambda: load("spence_15").spence_15(np.arange(1, 21)),
        "spence.21": lambda: load("spence_21").spence_21(np.arange(1, 21)),
    }
    for name, fn in cases.items():
        value = fn()
        text = repr(value)
        (OUT / f"locfit_{name.replace('.', '_')}_python.txt").write_text(text + "\n")
        r_ms = float("nan")
        py_ms = timed(fn)
        results[name] = (r_ms, py_ms, text)
    (OUT / "locfit_helpers_timing.txt").write_text(
        "\n".join(f"{k},R_ms={v[0]},translated_ms={v[1]}" for k, v in results.items()) + "\n"
    )
    print("R reference: packages/locfit/docs/output/locfit_helpers_r.txt")
    for name in results:
        print(f"{name}: reference generated; Python value written")


if __name__ == "__main__":
    main()
