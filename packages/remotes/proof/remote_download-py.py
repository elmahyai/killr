import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.remote import local_remote, remote_download

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

path = tempfile.mkdtemp()
with open(os.path.join(path, "DESCRIPTION"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write("Package: foo\nVersion: 1.0.0\n")


def package_of(bundle: str) -> str:
    with open(os.path.join(bundle, "DESCRIPTION"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("Package:"):
                return line.split(":", 1)[1].strip()
    raise SystemExit("DESCRIPTION has no Package field")


def one():
    return remote_download(local_remote(path))


value = package_of(one())
if value != "foo":
    raise SystemExit(repr(value))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    bundle = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if package_of(bundle) != value:
        raise SystemExit(bundle)

sentence = (
    "remote_download on a local directory copies a directory whose "
    "DESCRIPTION says Package: foo."
)
(out_dir / "remote_download-python.txt").write_text(sentence + "\n", encoding="utf-8")

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
