import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.update_packages import update_packages

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

lib = tempfile.mkdtemp(prefix="lib")
if update_packages([], lib=lib, quiet=True, upgrade="never") is not None:
    raise SystemExit("character() did not return None")
if os.listdir(lib):
    raise SystemExit(os.listdir(lib))


def one():
    return update_packages("remotes", lib=lib, quiet=True, upgrade="never")


value = one()
if value is not None:
    raise SystemExit(repr(value))
if os.listdir(lib):
    raise SystemExit("remotes was installed into the temp library")

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    if got is not None:
        raise SystemExit(repr(got))
if os.listdir(lib):
    raise SystemExit("library changed during timing")

sentence = 'update_packages("remotes", upgrade = "never") returns NULL.'
(out / "update_packages-python.txt").write_text(sentence + "\n", encoding="utf-8")
print(json.dumps({"value": None, "median_ms": statistics.median(elapsed)}))
