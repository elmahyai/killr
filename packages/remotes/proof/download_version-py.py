import json
import os
import statistics
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from remotes.download_version import download, download_version, download_version_url

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "download_version-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)

repos = "https://cloud.r-project.org"
kind = "source"


def description_basename(path: str) -> str:
    with tarfile.open(path, "r:gz") as archive:
        name = next(item for item in archive.getnames() if item.endswith("DESCRIPTION"))
        text = archive.extractfile(name).read().decode()
    fields = {}
    for line in text.splitlines():
        if ":" in line and not line[:1].isspace():
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields["Package"] + "_" + fields["Version"] + ".tar.gz"


path = download_version("remotes", "2.5.0", repos=repos, type=kind)
with open(path, "rb") as handle:
    magic = handle.read(2)
if magic != b"\x1f\x8b":
    raise SystemExit("downloaded file does not start with gzip magic")
base = description_basename(path)
url = download_version_url("remotes", "2.5.0", repos, kind)
if os.path.basename(url) != base:
    raise SystemExit(f"{os.path.basename(url)} != {base}")

sentence = (
    'download_version("remotes", "2.5.0", repos = "https://cloud.r-project.org", '
    f'type = "source") downloads {base}.'
)
out.write_text(sentence + "\n", encoding="utf-8")

dest = os.path.join(tempfile.gettempdir(), "dv-py")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    download(dest, url)
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"basename": base, "median_ms": statistics.median(elapsed)}))
