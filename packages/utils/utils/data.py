"""Load one named dataset from a package lazy-load database.

This is the path ``utils::data(list = x, package = package)`` uses for the
datasets that ship with R. The ``Rdata.rdb`` records use compression code 3:
four big-endian bytes of uncompressed length, a type byte, then the payload.
Type ``Z`` is raw LZMA2 at preset 6, the same filter R's ``R_compress3`` writes.
The payload is serialization version 3.
"""

from __future__ import annotations

import bz2
import lzma
import os
import struct
import warnings
import zlib
from pathlib import Path


def data(*names, list=None, package=None, lib_loc=None, verbose=False, envir=None, overwrite=True):
    """Load named datasets and return them keyed by the requested name.

    ``list`` is the character vector of names, matching R. Extra positional
    names are included too. A missing name warns. ``envir`` and ``overwrite``
    are accepted; the objects are returned instead of being assigned.
    """
    requested = [str(name) for name in names]
    if list is not None:
        if isinstance(list, str):
            requested.append(list)
        else:
            requested.extend(str(name) for name in list)
    if not requested:
        raise ValueError("data() listing is not implemented; pass a dataset name")
    loaded = {}
    for name in requested:
        found = _load_one(name, package, lib_loc)
        if found is None:
            warnings.warn(f"data set '{name}' not found", stacklevel=2)
        else:
            loaded[name] = found
    return loaded


def _load_one(name: str, package, lib_loc):
    for directory in _data_dirs(package, lib_loc):
        index_path = directory / "Rdata.rds"
        if not index_path.is_file():
            continue
        index = _read_index(index_path)
        if name not in index:
            continue
        objects = index[name]
        if isinstance(objects, str):
            objects = [objects]
        loaded = _lazy_load(directory / "Rdata", objects)
        if name in loaded:
            return loaded[name]
        if len(loaded) == 1:
            return next(iter(loaded.values()))
    return None


def _read_index(path: Path) -> dict:
    from readr.rds import read_rds

    index = read_rds(path)
    if not isinstance(index, dict):
        raise ValueError(f"{path} is not a named list")
    return index


def _lazy_load(filebase: Path, names: list) -> dict:
    from readr.rds import parse_rds, read_rds

    header = read_rds(Path(str(filebase) + ".rdx"))
    if not isinstance(header, dict):
        raise ValueError(f"{filebase}.rdx is not a named list")
    compressed = header.get("compressed")
    if isinstance(compressed, list):
        compressed = compressed[0] if compressed else None
    if compressed != 3 and compressed != 3.0:
        raise ValueError(f"lazy-load compression {compressed} is not supported")
    variables = header["variables"]
    blob = Path(str(filebase) + ".rdb").read_bytes()
    found = {}
    for name in names:
        if name not in variables:
            continue
        offset, length = variables[name]
        chunk = blob[int(offset) : int(offset) + int(length)]
        found[name] = parse_rds(_decompress3(chunk))
    return found


def _decompress3(chunk: bytes) -> bytes:
    if len(chunk) < 5:
        raise ValueError("lazy-load record is too short")
    outlen = struct.unpack(">I", chunk[:4])[0]
    kind = chr(chunk[4])
    payload = chunk[5:]
    if kind == "Z":
        raw = lzma.decompress(
            payload,
            format=lzma.FORMAT_RAW,
            filters=[{"id": lzma.FILTER_LZMA2, "preset": 6}],
        )
    elif kind == "2":
        raw = bz2.decompress(payload)
    elif kind == "1":
        raw = zlib.decompress(payload)
    elif kind == "0":
        raw = payload
    else:
        raise ValueError(f"unknown lazy-load type {kind!r}")
    if len(raw) != outlen:
        raise ValueError("lazy-load length does not match")
    return raw


def _data_dirs(package, lib_loc):
    packages = []
    if package is None:
        packages = None
    elif isinstance(package, str):
        packages = [package]
    else:
        packages = [str(item) for item in package]
    roots = _library_dirs(lib_loc)
    if package is None:
        roots = [Path.cwd(), *roots]
    found = []
    for root in roots:
        if packages is None:
            if not root.is_dir():
                continue
            children = [path for path in root.iterdir() if (path / "data").is_dir()]
        else:
            children = [root / name for name in packages]
        for path in children:
            data = path / "data"
            if data.is_dir():
                found.append(data)
    return found


def _library_dirs(lib_loc):
    raw = []
    if lib_loc is not None:
        if isinstance(lib_loc, (str, Path)):
            raw.append(str(lib_loc))
        else:
            raw.extend(str(path) for path in lib_loc)
    for key in ("R_LIBS", "R_LIBS_USER", "R_LIBS_SITE"):
        value = os.environ.get(key)
        if value:
            raw.extend(part for part in value.split(os.pathsep) if part)
    home = os.environ.get("R_HOME")
    if not home and Path("/usr/lib/R/library").is_dir():
        home = "/usr/lib/R"
    if home:
        raw.append(str(Path(home) / "library"))
    raw.append("/usr/lib/R/site-library")
    raw.append("/usr/local/lib/R/site-library")
    seen = []
    for item in raw:
        path = Path(item)
        if path.is_dir() and path not in seen:
            seen.append(path)
    return seen
