import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_bitbucket import bitbucket_remote, install_bitbucket
from remotes.install_core import InstallError

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

lib = tempfile.mkdtemp(prefix="lib")
try:
    installed = install_bitbucket(
        "djnavarro/lsr", dependencies=False, upgrade="never", quiet=True, build=False, lib=lib
    )
except InstallError:
    installed = "error"


def one():
    remote = bitbucket_remote("djnavarro/lsr")
    return (remote.username, remote.repo, remote.ref)


value = one()
if value != ("djnavarro", "lsr", "HEAD"):
    raise SystemExit(repr(value))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != value:
        raise SystemExit(repr(got))

sentence = 'install_bitbucket("djnavarro/lsr") would install lsr from djnavarro/lsr at HEAD.'
(out / "install_bitbucket-python.txt").write_text(sentence + "\n", encoding="utf-8")
shown = installed[0] if installed == ["lsr"] else "error"
print(json.dumps({
    "username": "djnavarro",
    "repo": "lsr",
    "ref": "HEAD",
    "installed": shown,
    "median_ms": statistics.median(elapsed),
}))
