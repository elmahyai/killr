"""Python side of the sass proof: the Rust libsass crate (sass_kernel) on the same input.

Run from the repository root after the R script:
    .venv/bin/python packages/sass/proof/sass_rust.py
"""

import statistics
import time
from pathlib import Path

import sass_kernel

root = Path.cwd()
proof = root / "packages" / "sass" / "proof"
out = root / "packages" / "sass" / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

input_text = (proof / "input.scss").read_bytes().decode("utf-8")

options = dict(
    output_style="expanded",
    include_path=[str(proof / "fixtures")],
    precision=5,
    indented_syntax=False,
    source_comments=False,
    indent="  ",
    linefeed="lf",
)


def compile_once():
    return sass_kernel.compile_scss(input_text, **options)


# One untimed call, then 20 timed calls.
css = compile_once()

times = []
for _ in range(20):
    t0 = time.perf_counter()
    css = compile_once()
    times.append(time.perf_counter() - t0)

(out / "sass_rust.css").write_bytes(css.encode("utf-8"))

median = statistics.median(times)
timing = [
    "language: Python (Rust libsass crate sass_kernel)",
    "timer: time.perf_counter()",
    "calls: 20 timed after 1 untimed",
    f"median_seconds: {median:.10g}",
    "times_seconds: " + " ".join(f"{t:.10g}" for t in times),
]
(out / "sass_rust_timing.txt").write_text("\n".join(timing) + "\n", encoding="utf-8")

# Compare with the R output byte for byte.
r_css_path = out / "sass_r.css"
r_timing_path = out / "sass_r_timing.txt"
r_css = r_css_path.read_bytes()
rust_css = (out / "sass_rust.css").read_bytes()
exact = r_css == rust_css

r_median = None
for line in r_timing_path.read_text(encoding="utf-8").splitlines():
    if line.startswith("median_seconds: "):
        r_median = float(line.split(": ", 1)[1])

compare = [
    f"exact_match: {exact}",
    f"r_bytes: {len(r_css)}",
    f"rust_bytes: {len(rust_css)}",
    f"r_median_seconds: {r_median:.10g}",
    f"rust_median_seconds: {median:.10g}",
    f"speedup_r_over_rust: {r_median / median:.4g}",
]
(out / "sass_compare.txt").write_text("\n".join(compare) + "\n", encoding="utf-8")
print("\n".join(compare))
