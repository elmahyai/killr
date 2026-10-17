import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.remote import local_remote, remote_metadata

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

path = tempfile.mkdtemp()
with open(os.path.join(path, "DESCRIPTION"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write("Package: foo\nVersion: 1.0.0\n")


def one():
    return remote_metadata(local_remote(path))


value = one()
url_matches = value["RemoteUrl"] == os.path.realpath(path)
if value["RemoteType"] != "local" or not url_matches or value["RemoteSubdir"] is not None:
    raise SystemExit(repr(value))

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got != value:
        raise SystemExit(repr(got))

sentence = (
    "remote_metadata on a local directory returns RemoteType local "
    "and RemoteUrl equal to normalizePath."
)
(out_dir / "remote_metadata-python.txt").write_text(sentence + "\n", encoding="utf-8")

print(json.dumps({
    "value": {
        "RemoteType": value["RemoteType"],
        "url_matches": url_matches,
        "RemoteSubdir": value["RemoteSubdir"],
    },
    "median_ms": statistics.median(elapsed),
}))
