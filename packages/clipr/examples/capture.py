"""Run the clipr examples and save what R and Python print."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"
ENV = os.environ.copy()
ENV["CLIPR_ALLOW"] = "TRUE"
ENV["R_LIBS_USER"] = str(Path.home() / "R" / "library")
ENV["PATH"] = f"{Path.home() / '.local' / 'bin'}:{ENV.get('PATH', '')}"
ENV.setdefault("DISPLAY", ":0")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _seed()
    _write("write_clip-r.txt", _r(WRITE_R))
    _write("write_clip-python.txt", _py(WRITE_PY))
    _write("read_clip-r.txt", _r(READ_R))
    _write("read_clip-python.txt", _py(READ_PY))
    _write("read_clip_tbl-r.txt", _r(TABLE_R))
    _write("read_clip_tbl-python.txt", _py(TABLE_PY))
    _write("clear_clip-r.txt", _r(CLEAR_R))
    _write("clear_clip-python.txt", _py(CLEAR_PY))
    _write("clipr_available-r.txt", _r(AVAILABLE_R))
    _write("clipr_available-python.txt", _py(AVAILABLE_PY))
    _write("dr_clipr-r.txt", _r(DR_R))
    _write("dr_clipr-python.txt", _py(DR_PY))
    _write("write_last_clip-r.txt", _r(LAST_R))
    _write("write_last_clip-python.txt", _py(LAST_PY))
    print(f"wrote {OUTPUT}")


def _seed() -> None:
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=b"seed",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=ENV,
        check=True,
    )


def _r(script: str) -> str:
    return _run(["Rscript", "-e", script])


def _py(script: str) -> str:
    return _run([sys.executable, "-c", script])


def _run(argv: list[str]) -> str:
    """Collect output from files. A pipe would stay open: xclip inherits it and daemonizes."""
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        out_path = Path(directory) / "out"
        err_path = Path(directory) / "err"
        with out_path.open("w") as out, err_path.open("w") as err:
            result = subprocess.run(argv, stdout=out, stderr=err, env=ENV, check=False)
        stdout = out_path.read_text()
        stderr = err_path.read_text()
    if result.returncode != 0:
        raise RuntimeError(stderr or stdout)
    return stdout + stderr


def _write(name: str, text: str) -> None:
    (OUTPUT / name).write_text(text if text.endswith("\n") else text + "\n")


WRITE_R = r"""
suppressPackageStartupMessages(library(clipr))
text <- "Write to clipboard"
print(write_clip(text, return_new = TRUE))
multiline <- c("Write", "to", "clipboard")
print(write_clip(multiline, return_new = TRUE))
print(write_clip(multiline, breaks = ",", return_new = TRUE))
tbl <- data.frame(a = c(1, 2, 3), b = c(4, 5, 6))
print(write_clip(tbl, return_new = TRUE))
"""

WRITE_PY = r"""
from clipr import write_clip
text = "Write to clipboard"
print(write_clip(text, return_new=True))
multiline = ["Write", "to", "clipboard"]
print(write_clip(multiline, return_new=True))
print(write_clip(multiline, breaks=",", return_new=True))
tbl = {"a": [1, 2, 3], "b": [4, 5, 6]}
print(write_clip(tbl, return_new=True))
"""

READ_R = r"""
suppressPackageStartupMessages(library(clipr))
write_clip("Write to clipboard")
print(read_clip())
"""

READ_PY = r"""
from clipr import read_clip, write_clip
write_clip("Write to clipboard")
print(read_clip())
"""

TABLE_R = r"""
suppressPackageStartupMessages(library(clipr))
x <- c("Name's\tAge", "Alice\t30", "Bob\t25")
print(read_clip_tbl(x))
"""

TABLE_PY = r"""
from clipr import read_clip_tbl
x = ["Name's\tAge", "Alice\t30", "Bob\t25"]
print(read_clip_tbl(x))
"""

CLEAR_R = r"""
suppressPackageStartupMessages(library(clipr))
write_clip("to-clear")
print(clear_clip())
print(read_clip())
"""

CLEAR_PY = r"""
from clipr import clear_clip, read_clip, write_clip
write_clip("to-clear")
print(clear_clip())
print(read_clip())
"""

AVAILABLE_R = r"""
suppressPackageStartupMessages(library(clipr))
print(clipr_available())
"""

AVAILABLE_PY = r"""
from clipr import clipr_available
print(clipr_available())
"""

DR_R = r"""
suppressPackageStartupMessages(library(clipr))
dr_clipr()
"""

DR_PY = r"""
from clipr import dr_clipr
dr_clipr()
"""

LAST_R = r"""
suppressPackageStartupMessages(library(clipr))
invisible("Write to clipboard")
print(write_last_clip(return_new = TRUE))
"""

LAST_PY = r"""
from clipr import write_last_clip
print(write_last_clip("Write to clipboard", return_new=True))
"""


if __name__ == "__main__":
    main()
