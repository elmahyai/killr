import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.github_remote import github_remote
from remotes.install_core import InstallError
from remotes.install_github import install_github

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

spec = "praise=gaborcsardi/praise"
lib = tempfile.mkdtemp(prefix="lib")
try:
    installed = install_github(
        spec,
        auth_token=None,
        dependencies=False,
        upgrade="never",
        quiet=True,
        build=False,
        lib=lib,
    )
except InstallError as exc:
    installed = str(exc)


def one():
    remote = github_remote(spec, auth_token=None)
    return (remote.package, remote.username, remote.repo, remote.ref)


value = one()
if value != ("praise", "gaborcsardi", "praise", "HEAD"):
    raise SystemExit(repr(value))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != value:
        raise SystemExit(repr(got))

sentence = 'install_github("praise=gaborcsardi/praise") would install praise from gaborcsardi/praise at HEAD.'
(out / "install_github-python.txt").write_text(sentence + "\n", encoding="utf-8")
shown = installed
if isinstance(shown, list):
    shown = shown[0] if len(shown) == 1 else shown
if isinstance(shown, str) and "\n" in shown:
    shown = "error"
print(json.dumps({
    "package": "praise",
    "username": "gaborcsardi",
    "repo": "praise",
    "ref": "HEAD",
    "installed": shown,
    "median_ms": statistics.median(elapsed),
}))
