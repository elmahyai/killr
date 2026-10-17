"""Inspect the header of an R data file."""

import gzip
import re
from pathlib import Path

_MAGIC = re.compile(rb"RD[ABX][1-9]")


def _header(path, compress):
    if compress == "gzip":
        with gzip.open(path, "rb") as handle:
            return handle.read(5)
    return Path(path).read_bytes()[:5]


def check_rda_files(paths):
    """Size, ASCII flag, compression, and format version of .rda files."""
    if isinstance(paths, (str, Path)):
        paths = [paths]
    paths = [Path(path) for path in paths]
    if len(paths) == 1 and paths[0].is_dir():
        directory = paths[0]
        paths = sorted(directory.glob("*.rda")) + sorted(directory.glob("*.RData"))
        paths = [path for path in paths if path.name != ".RData"]
    rows = []
    for path in paths:
        row = {"path": str(path), "size": None, "ASCII": None, "compress": None, "version": None}
        if path.is_file():
            data = path.read_bytes()
            row["size"] = len(data)
            magic = data[:5]
            if len(magic) >= 2 and magic[0] == 31 and magic[1] == 139:
                row["compress"] = "gzip"
            elif magic[:3] == b"BZh":
                row["compress"] = "bzip2"
            elif len(magic) >= 5 and magic[0] == 253 and magic[1:5] == b"7zXZ":
                row["compress"] = "xz"
            elif _MAGIC.search(magic):
                row["compress"] = "none"
            else:
                row["compress"] = "unknown"
            header = _header(path, row["compress"])
            if _MAGIC.search(header):
                row["ASCII"] = header[2:3] == b"A"
                row["version"] = int(header[3:4])
        rows.append(row)
    return rows
