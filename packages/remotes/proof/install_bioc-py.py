import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_bioc import install_bioc

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

lib = tempfile.mkdtemp(prefix="lib")


def one():
    return install_bioc(
        "3.21/BiocVersion",
        dependencies=False,
        upgrade="never",
        quiet=True,
        build=False,
        lib=lib,
        git="external",
    )


value = one()
if value != ["BiocVersion"]:
    raise SystemExit(repr(value))
with open(os.path.join(lib, "BiocVersion", "DESCRIPTION"), encoding="utf-8") as handle:
    text = handle.read()
version = next(line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("Version:"))
if version != "3.21.1":
    raise SystemExit(version)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != ["BiocVersion"]:
        raise SystemExit(repr(got))

sentence = "install_bioc() returns BiocVersion 3.21.1."
(out / "install_bioc-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"name": "BiocVersion", "version": version, "median_ms": statistics.median(elapsed)}))
