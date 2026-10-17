import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_version import install_version

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

pkg = tempfile.mkdtemp(prefix="minipkg")
with open(os.path.join(pkg, "DESCRIPTION"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write(
        "Package: minipkg\nVersion: 0.0.1\nTitle: Minimal\n"
        "Description: A minimal package for a check.\nLicense: MIT\n"
    )
with open(os.path.join(pkg, "NAMESPACE"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write('exportPattern("^[^.]")\n')
root = tempfile.mkdtemp(prefix="cran")
contrib = os.path.join(root, "src", "contrib")
os.makedirs(contrib)
subprocess.run(
    ["R", "CMD", "build", pkg, "--no-manual", "--no-build-vignettes"],
    cwd=contrib,
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
with open(os.path.join(contrib, "PACKAGES"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write("Package: minipkg\nVersion: 0.0.1\n")
repos = "file://" + os.path.realpath(root)
lib = tempfile.mkdtemp(prefix="lib")


def one():
    return install_version(
        "minipkg",
        "0.0.1",
        repos=repos,
        type="source",
        dependencies=False,
        upgrade="never",
        quiet=True,
        lib=lib,
    )


value = one()
if value != ["minipkg"]:
    raise SystemExit(repr(value))
with open(os.path.join(lib, "minipkg", "DESCRIPTION"), encoding="utf-8") as handle:
    text = handle.read()
version = next(line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("Version:"))
if version != "0.0.1" or any(line.startswith("RemoteType:") for line in text.splitlines()):
    raise SystemExit(text)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != ["minipkg"]:
        raise SystemExit(repr(got))

sentence = "install_version() returns minipkg 0.0.1."
(out / "install_version-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"name": "minipkg", "version": version, "median_ms": statistics.median(elapsed)}))
