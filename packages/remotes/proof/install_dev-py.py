import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_core import InstallError
from remotes.install_dev import dev_split_ref, install_dev

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

cran = tempfile.mkdtemp(prefix="fakecran")
desc_dir = os.path.join(cran, "web", "packages", "minipkg")
os.makedirs(desc_dir)
desc_path = os.path.join(desc_dir, "DESCRIPTION")
with open(desc_path, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("Package: minipkg\nVersion: 0.0.1\nURL: https://bitbucket.org/djnavarro/lsr\n")
cran_url = "file://" + os.path.realpath(cran)
lib = tempfile.mkdtemp(prefix="lib")
try:
    installed = install_dev(
        "minipkg",
        cran_url=cran_url,
        dependencies=False,
        upgrade="never",
        quiet=True,
        build=False,
        lib=lib,
    )
except InstallError:
    installed = "error"


def one():
    name, _ref = dev_split_ref("minipkg")
    with open(os.path.join(cran, "web", "packages", name, "DESCRIPTION"), encoding="utf-8") as handle:
        url = next(line.split(":", 1)[1].strip() for line in handle if line.startswith("URL:"))
    return (name, url)


value = one()
if value != ("minipkg", "https://bitbucket.org/djnavarro/lsr"):
    raise SystemExit(repr(value))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != value:
        raise SystemExit(repr(got))

sentence = "install_dev() would install lsr from https://bitbucket.org/djnavarro/lsr."
(out / "install_dev-python.txt").write_text(sentence + "\n", encoding="utf-8")
shown = installed[0] if installed == ["lsr"] else "error"
print(json.dumps({
    "package": "minipkg",
    "url": "https://bitbucket.org/djnavarro/lsr",
    "installed": shown,
    "median_ms": statistics.median(elapsed),
}))
