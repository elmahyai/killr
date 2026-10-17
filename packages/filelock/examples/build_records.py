"""Time lock and unlock against R, and capture the runnable example."""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = "/home/ahmed/killr_projects/killr/.venv/bin/python"
ENV = {**os.environ, "PYTHONPATH": str(ROOT)}

R_LOCK = r"""
suppressPackageStartupMessages(library(filelock))
one <- function() {
  path <- tempfile("filelock")
  lck <- lock(path)
  txt <- paste(capture.output(print(lck)), collapse = "\n")
  txt <- sub(path, "PATH", txt, fixed = TRUE)
  unlock(lck)
  txt
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":\"%s\",\"median_ms\":%.17g}\n", gsub("\"", "\\\"", value), median(elapsed) * 1000))
"""

R_UNLOCK = r"""
suppressPackageStartupMessages(library(filelock))
one <- function() {
  path <- tempfile("filelock")
  lck <- lock(path)
  unlock(lck)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", if (isTRUE(value)) "true" else "false", median(elapsed) * 1000))
"""

PY_LOCK = """
import json
import statistics
import tempfile
import time

from filelock import lock, unlock

def one():
    path = tempfile.mktemp(prefix="filelock")
    held = lock(path)
    text = str(held).replace(path, "PATH")
    unlock(held)
    return text

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
"""

PY_UNLOCK = """
import json
import statistics
import tempfile
import time

from filelock import lock, unlock

def one():
    path = tempfile.mktemp(prefix="filelock")
    held = lock(path)
    return unlock(held)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
"""

EXAMPLE_R = r"""
mylockfile <- tempfile()
lck <- lock(mylockfile)
print(lck)
lock(mylockfile, timeout = 0)
lock(mylockfile, timeout = 5000)
lock(mylockfile, timeout = Inf)
invisible(unlock(lck))
"""

EXAMPLE_PY = """
import tempfile
from filelock import lock, unlock

mylockfile = tempfile.mktemp()
lck = lock(mylockfile)
print(lck)
print(lock(mylockfile, timeout=0))
print(lock(mylockfile, timeout=5000))
print(lock(mylockfile, timeout=float("inf")))
unlock(lck)
"""

EXAMPLE_TEXT = """\
mylockfile <- tempfile()
lck <- lock(mylockfile)
print(lck)
lock(mylockfile, timeout = 0)
lock(mylockfile, timeout = 5000)
lock(mylockfile, timeout = Inf)
"""

DESCRIPTION = (
    "There are two kinds of locks, exclusive and shared, see the exclusive argument and other details below."
)
DETAILS = """\
Always use special files for locking. Do not place the lock on a file you want to read or write. Create a special file, for example by appending .lock, and lock that. lock() creates the file when it does not exist. Reading or writing a locked file has undefined behavior.

All locks set by this package might be advisory. On Unix the lock is an fcntl record lock kept on an open descriptor. A second handle in the same process shares that descriptor. Closing any descriptor for the file releases every lock this process holds on it.

unlock() drops one handle. The kernel lock remains until the last handle is released. Releasing an already unlocked handle returns true."""


def _run(argv: list[str], script: str) -> dict:
    result = subprocess.run(argv, input=script, text=True, capture_output=True, env=ENV)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    line = next(item for item in reversed(result.stdout.splitlines()) if item.startswith("{"))
    return json.loads(line)


def _capture(argv: list[str], script: str) -> str:
    result = subprocess.run(argv, input=script, text=True, capture_output=True, env=ENV)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout if result.stdout.endswith("\n") else result.stdout + "\n"


def _doc(name: str, usage: str, example: str, python_example: str) -> dict:
    return {
        "name": name,
        "title": "Advisory File Locking and Unlocking",
        "origin": {
            "description": DESCRIPTION,
            "usage": usage,
            "arguments": [
                {
                    "name": "path",
                    "text": "Path to the file to lock. If the file does not exist, it will be created, but the directory of the file must exist. Do not place the lock on a file that you want to read from or write to.",
                },
                {
                    "name": "exclusive",
                    "text": "Whether to acquire an exclusive lock. A non-exclusive lock is a shared lock. Multiple processes can hold a shared lock on the same file.",
                },
                {
                    "name": "timeout",
                    "text": "Timeout to acquire the lock in milliseconds. Inf waits indefinitely. Zero returns immediately.",
                },
                {
                    "name": "lock",
                    "text": "The lock object to unlock. Unlocking an already unlocked lock is not an error. An unlocked lock cannot be locked again.",
                },
            ],
            "details": DETAILS,
            "value": "lock returns a filelock_lock object, or NULL when the wait times out. unlock returns TRUE.",
            "example": example,
            "output": f"output/{name}-r.txt",
        },
        "translation": {
            "description": DESCRIPTION,
            "usage": usage,
            "arguments": [
                {
                    "name": "path",
                    "text": "Path to the file to lock. If the file does not exist, it will be created, but the directory of the file must exist. Do not place the lock on a file that you want to read from or write to.",
                },
                {
                    "name": "exclusive",
                    "text": "Whether to acquire an exclusive lock. A non-exclusive lock is a shared lock. Multiple processes can hold a shared lock on the same file.",
                },
                {
                    "name": "timeout",
                    "text": "Timeout to acquire the lock in milliseconds. Inf waits indefinitely. Zero returns immediately.",
                },
                {
                    "name": "lock",
                    "text": "The lock object to unlock. Unlocking an already unlocked lock is not an error. An unlocked lock cannot be locked again.",
                },
            ],
            "details": DETAILS,
            "value": "lock returns a FileLock, or None when the wait times out. unlock returns True.",
            "example": python_example,
            "output": f"output/{name}-python.txt",
        },
    }


def main() -> None:
    proof = ROOT / "proof"
    output = ROOT / "docs" / "output"
    proof.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    pairs = [
        ("lock", "filelock.lock", "Acquire an exclusive or shared fcntl lock.", 'lock(tempfile()) then print', R_LOCK, PY_LOCK),
        ("unlock", "filelock.unlock", "Release one lock handle.", "unlock(lock(tempfile()))", R_UNLOCK, PY_UNLOCK),
    ]
    functions = []
    for name, python, done, case, r_code, py_code in pairs:
        (proof / f"{name}-r.R").write_text(r_code)
        (proof / f"{name}-py.py").write_text(py_code)
        print("checking", name, flush=True)
        r_result = _run(["Rscript", "-"], r_code)
        py_result = _run([PY, "-"], py_code)
        matches = r_result["value"] == py_result["value"]
        if not matches:
            print(" MISMATCH", r_result["value"], py_result["value"])
        speedup = r_result["median_ms"] / py_result["median_ms"] if py_result["median_ms"] else None
        functions.append(
            {
                "name": name,
                "translated": matches,
                "python": python,
                "loads": [],
                "uses": [],
                "done": done,
                "not_done": "" if matches else "The check against R did not match.",
                "blocked_by": [],
                "assigned": "",
                "check": {
                    "case": case,
                    "r_ms": r_result["median_ms"],
                    "translated_ms": py_result["median_ms"],
                    "speedup": speedup,
                    "matches": matches,
                    "max_abs_diff": 0.0 if matches else 1.0,
                    "tolerance": 1e-8,
                    "proof": {"r": r_code, "python": py_code},
                },
            }
        )
    example_path = ROOT / "examples" / "example.R"
    example_path.write_text(EXAMPLE_R)
    runner = (
        "suppressPackageStartupMessages(library(filelock))\n"
        "options(width = 80)\n"
        f"output <- capture.output(source({json.dumps(str(example_path))}, echo = FALSE, print.eval = TRUE))\n"
        "cat(paste(output, collapse = '\\n'))\n"
        "if (length(output)) cat('\\n')\n"
    )
    r_example = _capture(["Rscript", "-e", runner], "")
    py_example = _capture([PY, "-c", EXAMPLE_PY], "")
    for name in ("lock", "unlock"):
        (output / f"{name}-r.txt").write_text(r_example)
        (output / f"{name}-python.txt").write_text(py_example)
        usage = "lock(path, exclusive = TRUE, timeout = Inf)\n\nunlock(lock)"
        (ROOT / "docs" / f"{name}.json").write_text(
            json.dumps(_doc(name, usage, EXAMPLE_TEXT, textwrap.dedent(EXAMPLE_PY).strip()), indent=2) + "\n"
        )
    record = {
        "name": "filelock",
        "cran_version": "1.0.3",
        "inventory": "complete",
        "status": "complete" if all(item["check"]["matches"] for item in functions) else "in_progress",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "lock and unlock use POSIX fcntl record locks through the Python standard library. A second handle in this process shares the open descriptor. Rust File::lock is flock, so it does not contend with these locks.",
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print("matches", [item["check"]["matches"] for item in functions])


if __name__ == "__main__":
    main()
