"""Load installed package help (Rd) databases and read Rd metadata tags."""

from __future__ import annotations

import gzip
import os
import struct
import sys
import zlib
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tools.session import standard_package_names


class _Reader:
    def __init__(self, data: bytes, start: int):
        self.data = data
        self.i = start
        self.refs: list[object] = [None]

    def i32(self) -> int:
        value = struct.unpack_from(">i", self.data, self.i)[0]
        self.i += 4
        return value

    def read(self):
        flags = self.i32()
        kind = flags & 255
        has_attr = flags & (1 << 9)
        has_tag = flags & (1 << 10)
        if kind == 255:
            index = flags >> 8
            if index == 0:
                index = self.i32()
            return self.refs[index]
        if kind in (254, 241, 242, 253, 252, 251, 250):
            return None
        if kind == 247:
            self.i32()
            self.i32()
            node = ("persist", self.read())
            self.refs.append(node)
            return node
        if kind == 9:
            n = self.i32()
            if n < 0:
                return None
            text = self.data[self.i : self.i + n].decode("utf-8", "replace")
            self.i += n
            return text
        if kind == 1:
            node = ("sym", self.read())
            self.refs.append(node)
            return node
        if kind in (2, 6, 3, 5, 17):
            if has_attr:
                self.read()
            tag = self.read() if has_tag else None
            return ("pair", tag, self.read(), self.read())
        if kind in (16, 19, 20):
            n = self._length()
            values = [self.read() for _ in range(n)]
            attrs = self.read() if has_attr else None
            label = "str" if kind == 16 else "vec"
            return (label, values, attrs)
        if kind in (10, 13):
            n = self._length()
            values = [self.i32() for _ in range(n)]
            attrs = self.read() if has_attr else None
            return ("int", values, attrs)
        if kind == 14:
            n = self._length()
            self.i += 8 * n
            attrs = self.read() if has_attr else None
            return ("real", n, attrs)
        if kind == 24:
            n = self._length()
            self.i += n
            attrs = self.read() if has_attr else None
            return ("raw", n, attrs)
        if kind == 25:
            attrs = self.read() if has_attr else None
            return ("s4", attrs)
        raise ValueError(f"unsupported RDS type {kind} at {self.i}")

    def _length(self) -> int:
        n = self.i32()
        if n < 0:
            n = struct.unpack_from(">q", self.data, self.i)[0]
            self.i += 8
        return n


def _parse_rds(blob: bytes):
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    if blob[:2] != b"X\n":
        raise ValueError("help database is not an XDR RDS stream")
    index = 2
    for _ in range(3):
        index += 4
    name_len = struct.unpack_from(">i", blob, index)[0]
    index += 4
    if name_len > 0:
        index += name_len
    return _Reader(blob, index).read()


def _pairs(attrs):
    while isinstance(attrs, tuple) and attrs and attrs[0] == "pair":
        yield attrs[1], attrs[2]
        attrs = attrs[3]


def _attr(node, name: str):
    if not isinstance(node, tuple) or len(node) < 3:
        return None
    for tag, value in _pairs(node[2]):
        if tag == ("sym", name):
            return value
    return None


def _strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, tuple) and node[0] == "str":
        return [item if isinstance(item, str) else "" for item in node[1]]
    return []


def rd_tag(node) -> str:
    texts = _strings(_attr(node, "Rd_tag"))
    return texts[0] if texts else ""


def _int_pair(node) -> tuple[int, int]:
    if isinstance(node, tuple) and node[0] == "int" and len(node[1]) >= 2:
        return int(node[1][0]), int(node[1][1])
    raise ValueError("help index entry is not an offset and a length")


def _library_dir() -> Path:
    home = os.environ.get("R_HOME", "/usr/lib/R")
    return Path(home) / "library"


def _find_package(package: str, lib_loc: Path | None = None) -> Path:
    roots = [lib_loc] if lib_loc is not None else [_library_dir()]
    for root in roots:
        path = Path(root) / package
        if (path / "DESCRIPTION").is_file():
            return path
    raise ValueError(f"there is no package called {package!r}")


def _fetch_rd_db(filebase: Path) -> dict[str, object]:
    index = _parse_rds(Path(str(filebase) + ".rdx").read_bytes())
    variables = _component(index, "variables")
    if variables is None:
        raise ValueError(f"installed help of package {filebase.name!r} is corrupt")
    compressed_node = _component(index, "compressed")
    compressed = True
    if isinstance(compressed_node, tuple) and compressed_node[0] == "int":
        compressed = bool(compressed_node[1] and compressed_node[1][0])
    raw = Path(str(filebase) + ".rdb").read_bytes()
    names = _strings(_attr(variables, "names"))
    found: dict[str, object] = {}
    for name, entry in zip(names, variables[1]):
        offset, length = _int_pair(entry)
        chunk = raw[offset : offset + length]
        payload = chunk[4:]
        if compressed:
            payload = zlib.decompress(payload)
        found[name] = _parse_rds(payload)
    return found


def _component(node, name: str):
    labels = _strings(_attr(node, "names"))
    if isinstance(node, tuple) and node[0] == "vec" and labels:
        for label, child in zip(labels, node[1]):
            if label == name:
                return child
    current = node
    while isinstance(current, tuple) and current and current[0] == "pair":
        if current[1] == ("sym", name):
            return current[2]
        current = current[3]
    return None


def _paths_first(node) -> int | None:
    first = _attr(node, "first")
    if isinstance(first, tuple) and first[0] == "int" and first[1]:
        return int(first[1][0])
    return None


def rd_db(package: str, lib_loc: Path | None = None) -> dict[str, object]:
    """Installed help topics for one package, keyed by Rd file name."""
    directory = _find_package(package, lib_loc)
    db_file = directory / "help" / package
    if not db_file.with_suffix(".rdx").is_file():
        raise ValueError(f"installed help of package {package!r} is corrupt")
    db = _fetch_rd_db(db_file)
    pathfile = directory / "help" / "paths.rds"
    if pathfile.is_file():
        paths_node = _parse_rds(pathfile.read_bytes())
        paths = _strings(paths_node) if isinstance(paths_node, tuple) else []
        if not paths and isinstance(paths_node, str):
            paths = [paths_node]
        first = _paths_first(paths_node)
        if first is not None:
            start = max(first - 1, 0)
            paths = [path[start:] for path in paths]
        if len(paths) == len(db):
            keys = list(db.keys())
            for key, path in zip(keys, paths):
                db[path] = db.pop(key)
    return db


def rd_tags(rd) -> list[str]:
    if not isinstance(rd, tuple) or rd[0] != "vec":
        return []
    return [rd_tag(child) for child in rd[1]]


def _rd_text(node) -> str:
    if isinstance(node, str):
        return node
    if not isinstance(node, tuple):
        return ""
    if node[0] == "str":
        if rd_tag(node) == "COMMENT":
            return ""
        return "".join(item or "" for item in node[1])
    if node[0] != "vec":
        return ""
    return "\n".join(_rd_text(child) for child in node[1])


def rd_get_metadata(rd, kind: str) -> list[str]:
    """Alias, concept, and other metadata tags from one Rd object."""
    tag = f"\\{kind}"
    pieces: list[str] = []
    if isinstance(rd, tuple) and rd[0] == "vec":
        for child in rd[1]:
            if rd_tag(child) != tag:
                continue
            text = _rd_text(child).strip()
            if kind == "concept":
                # USERMACRO \\I handling omitted; not used for alias kind.
                pass
            pieces.append(text)
    seen: set[str] = set()
    unique: list[str] = []
    for piece in pieces:
        if piece not in seen:
            seen.add(piece)
            unique.append(piece)
    return unique


def _one_package(package: str, kind: str, lib_loc: Path | None) -> dict[str, list[str]]:
    topics = rd_db(package, lib_loc=lib_loc)
    return {name: rd_get_metadata(topic, kind) for name, topic in topics.items()}


def _package_apply(
    packages: list[str],
    func: Callable[[str], object],
    *,
    verbose: bool = False,
    ncpus: int = 1,
) -> dict[str, object]:
    def one(package: str):
        if verbose:
            print(f"processing {package}", file=sys.stderr)
        try:
            return func(package)
        except Exception as exc:
            return exc

    if ncpus > 1 and len(packages) > 1:
        if os.name != "nt":
            with ProcessPoolExecutor(max_workers=ncpus) as pool:
                values = list(pool.map(one, packages))
        else:
            values = [one(package) for package in packages]
    else:
        values = [one(package) for package in packages]
    return dict(zip(packages, values))


def base_rd_metadata_db(
    kind: str,
    *,
    verbose: bool = True,
    ncpus: int = 1,
) -> dict[str, dict[str, list[str]]]:
    """Metadata from base-package Rd files, keyed by package then Rd file."""
    lib_loc = _library_dir()
    packages = standard_package_names()["base"]

    def worker(package: str):
        return _one_package(package, kind, lib_loc)

    return _package_apply(packages, worker, verbose=verbose, ncpus=ncpus)  # type: ignore[return-value]
