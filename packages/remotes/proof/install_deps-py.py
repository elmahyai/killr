import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_deps import install_deps

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

pkg = tempfile.mkdtemp(prefix="minipkg")
with open(os.path.join(pkg, "DESCRIPTION"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write(
        "Package: minipkg\nVersion: 0.0.1\nTitle: Minimal\n"
        "Description: A minimal package for a check.\nLicense: MIT\n"
    )
lib = tempfile.mkdtemp(prefix="lib")


def one():
    return install_deps(pkg, dependencies=False, upgrade="never", quiet=True, lib=lib)


value = one()
if value is not None:
    raise SystemExit(repr(value))
if os.listdir(lib):
    raise SystemExit(os.listdir(lib))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got is not None:
        raise SystemExit(repr(got))
if os.listdir(lib):
    raise SystemExit("library was not left empty")

sentence = "install_deps(dependencies = FALSE) returns NULL."
(out / "install_deps-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"value": None, "median_ms": statistics.median(elapsed)}))
