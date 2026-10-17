import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_core import InstallError
from remotes.install_svn import install_svn

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

lib = tempfile.mkdtemp(prefix="lib")
expected = (
    "Failed to install 'unknown package' from SVN:\n"
    "  SVN does not seem to be installed on your system."
)


def one():
    try:
        install_svn(
            "https://example.invalid/repo",
            dependencies=False,
            upgrade="never",
            quiet=True,
            lib=lib,
        )
    except InstallError as exc:
        return str(exc)
    raise SystemExit("install_svn did not fail")


value = one()
if value != expected:
    raise SystemExit(value)
if os.listdir(lib):
    raise SystemExit(os.listdir(lib))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != expected:
        raise SystemExit(got)

sentence = "install_svn() fails with: SVN does not seem to be installed on your system."
(out / "install_svn-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"message": "svn-missing", "median_ms": statistics.median(elapsed)}))
