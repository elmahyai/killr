import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_local import install_local

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
lib = tempfile.mkdtemp(prefix="lib")


def one():
    return install_local(
        pkg, dependencies=False, upgrade="never", quiet=True, build=False, lib=lib
    )


value = one()
if value != ["minipkg"]:
    raise SystemExit(repr(value))
with open(os.path.join(lib, "minipkg", "DESCRIPTION"), encoding="utf-8") as handle:
    text = handle.read()
version = next(line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("Version:"))
if version != "0.0.1":
    raise SystemExit(version)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != ["minipkg"]:
        raise SystemExit(repr(got))

sentence = "install_local() returns minipkg 0.0.1."
(out / "install_local-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"name": "minipkg", "version": version, "median_ms": statistics.median(elapsed)}))
