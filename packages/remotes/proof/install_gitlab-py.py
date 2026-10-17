import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_core import InstallError
from remotes.install_gitlab import gitlab_remote, install_gitlab

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

spec = "jimhester/covr"
lib = tempfile.mkdtemp(prefix="lib")
try:
    installed = install_gitlab(
        spec,
        auth_token=None,
        dependencies=False,
        upgrade="never",
        quiet=True,
        build=False,
        lib=lib,
    )
except InstallError:
    installed = "error"


def one():
    remote = gitlab_remote(spec)
    return (remote.username, remote.repo, remote.ref)


value = one()
if value != ("jimhester", "covr", "HEAD"):
    raise SystemExit(repr(value))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != value:
        raise SystemExit(repr(got))

sentence = 'install_gitlab("jimhester/covr") would install covr from jimhester/covr at HEAD.'
(out / "install_gitlab-python.txt").write_text(sentence + "\n", encoding="utf-8")
shown = installed
if isinstance(shown, list):
    shown = shown[0] if shown == ["covr"] else "error"
print(json.dumps({
    "username": "jimhester",
    "repo": "covr",
    "ref": "HEAD",
    "installed": shown,
    "median_ms": statistics.median(elapsed),
}))
