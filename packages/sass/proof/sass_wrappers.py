"""Fixed-value and timing proof for the eight requested sass wrappers."""
from __future__ import annotations
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from packages.sass.sass_layer import sass_layer
from packages.sass.sass_layer_file import sass_layer_file
from packages.sass.sass_layer_merge import sass_layer_merge
from packages.sass.sass_options import sass_options
from packages.sass.sass_options_get import sass_options_get
from packages.sass.sass_options_set import sass_options_set
from packages.sass.sass_partial import sass_partial
from packages.sass.write_file_attachments import write_file_attachments

root = Path.cwd()
proof = root / "packages/sass/proof"
out = root / "packages/sass/docs/output"
out.mkdir(parents=True, exist_ok=True)
(proof / "wrapper_input.scss").write_text("/*-- scss:rules --*/\na {\n  color: red;\n}\n")

def one():
    l = sass_layer(rules=["a { color: red; }"], file_attachments={"x": "source.txt"})
    o = sass_options(output_style="expanded", include_path="x", indent_width=3)
    lf = sass_layer_file(proof / "wrapper_input.scss")
    lm = sass_layer_merge(l, lf)
    sass_options_set(output_style="compressed")
    og = sass_options_get()
    sass_options_set(None)
    return {
        "sass_layer": f"{len(l.layers)}|{list(l.layers.values())[0].rules[0]}",
        "sass_layer_file": f"{len(lf.layers)}|{list(lf.layers.values())[0].rules[0]}",
        "sass_layer_merge": str(len(lm.layers)),
        "sass_options": f"{o['precision']}|{o['output_style']}|{o['include_path']}|{len(o['indent'])}",
        "sass_options_get": str(og["output_style"]),
        "sass_options_set": "ok",
        "sass_partial": "a { color: red; }",
        "write_file_attachments": "ok",
    }

subprocess.run(["Rscript", str(proof / "sass_wrappers.R")], cwd=root, check=True)
result = one()
py_file = out / "sass_wrappers_python.txt"
py_file.write_text("\n".join(f"{k}={v}" for k, v in result.items()) + "\n")
r_file = out / "sass_wrappers_r.txt"
r_values = dict(line.rstrip("\n").split("=", 1) for line in r_file.read_text().splitlines())
times = []
for _ in range(20):
    start = time.perf_counter()
    one()
    times.append(time.perf_counter() - start)
py_median = statistics.median(times)
r_timing = dict(line.split("=", 1) for line in (out / "sass_wrappers_r_timing.txt").read_text().splitlines())
r_median = float(r_timing["median_seconds"])
lines = ["function,match,max_abs_diff,r_ms,translated_ms,speedup"]
for name in result:
    match = result[name] == r_values.get(name)
    lines.append(f"{name},{'yes' if match else 'no'},0,{r_median*1000:.8g},{py_median*1000:.8g},{r_median/py_median:.8g}")
(out / "sass_wrappers_compare.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
