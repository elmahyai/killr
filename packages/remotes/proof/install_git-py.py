import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.install_git import install_git

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

repo = tempfile.mkdtemp(prefix="gitpkg")
with open(os.path.join(repo, "DESCRIPTION"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write(
        "Package: minipkg\nVersion: 0.0.1\nTitle: Minimal\n"
        "Description: A minimal package for a check.\nLicense: MIT\n"
    )
with open(os.path.join(repo, "NAMESPACE"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write('exportPattern("^[^.]")\n')


def git(*args):
    subprocess.run(["git", "-C", repo, *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


git("init", "-q")
git("config", "user.email", "a@b.c")
git("config", "user.name", "a")
git("add", "DESCRIPTION", "NAMESPACE")
git("commit", "-q", "-m", "init")
url = "file://" + os.path.realpath(repo)
lib = tempfile.mkdtemp(prefix="lib")


def one():
    return install_git(
        url, dependencies=False, upgrade="never", quiet=True, build=False, lib=lib, git="external"
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

sentence = "install_git() returns minipkg 0.0.1."
(out / "install_git-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"name": "minipkg", "version": version, "median_ms": statistics.median(elapsed)}))
