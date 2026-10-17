"""Read an installed package's rendered help and recover lifecycle tokens.

R stores each topic in a lazy-load database. A description section is pasted,
and a nested Rd list becomes ``list("...")``, which is where the badge name
``lifecycle-<stage>.svg`` is captured.
"""

from __future__ import annotations

import gzip
import os
import re
import struct
import zlib
from pathlib import Path

_WHICH = (
    "superseded",
    "deprecated",
    "questioning",
    "defunct",
    "experimental",
    "soft-deprecated",
    "retired",
)

_LIFECYCLE = re.compile(
    r"(?:lifecycle::badge\(\\\"|rlang:::lifecycle\(\\\"|list\(\"lifecycle-|https://www.tidyverse.org/lifecycle/#)([A-Za-z0-9_-]+)"
)

_ZERO = {"\\cr", "\\dots", "\\ldots", "\\R", "\\tab"}


class LifecycleError(Exception):
    pass


def lib_paths() -> list[Path]:
    found: list[Path] = []
    user = os.environ.get("R_LIBS_USER", "").strip()
    if user:
        found.append(Path(os.path.expanduser(user)))
    else:
        version = os.environ.get("R_VERSION", "4.5")
        found.append(Path.home() / "R" / f"x86_64-pc-linux-gnu-library/{version}")
    for extra in os.environ.get("R_LIBS", "").split(os.pathsep):
        extra = extra.strip()
        if extra:
            found.append(Path(os.path.expanduser(extra)))
    found.extend(
        [
            Path("/usr/local/lib/R/site-library"),
            Path("/usr/lib/R/site-library"),
            Path("/usr/lib/R/library"),
        ]
    )
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in found:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def r_installed(package: str) -> bool:
    return any((root / package / "DESCRIPTION").is_file() for root in lib_paths())


def require_r_packages(packages: list[str]) -> None:
    missing = [name for name in packages if not r_installed(name)]
    if not missing:
        return
    if len(missing) == 1:
        raise LifecycleError(f'The package "{missing[0]}" is required.')
    if len(missing) == 2:
        raise LifecycleError(f'The packages "{missing[0]}" and "{missing[1]}" are required.')
    quoted = ", ".join(f'"{name}"' for name in missing[:-1])
    raise LifecycleError(f'The packages {quoted}, and "{missing[-1]}" are required.')


def package_dir(package: str) -> Path:
    for root in lib_paths():
        path = root / package
        if (path / "DESCRIPTION").is_file():
            return path
    raise LifecycleError(f"there is no package called \u2018{package}\u2019")


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
        if kind == 254 or kind in (241, 242, 253, 252, 251, 250):
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


def parse_rds(blob: bytes):
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    if blob[:2] != b"X\n":
        raise ValueError("help database is not an XDR RDS stream")
    i = 2
    for _ in range(3):
        i += 4
    n = struct.unpack_from(">i", blob, i)[0]
    i += 4
    if n > 0:
        i += n
    return _Reader(blob, i).read()


def _pairs(attrs):
    while isinstance(attrs, tuple) and attrs and attrs[0] == "pair":
        yield attrs[1], attrs[2]
        attrs = attrs[3]


def _strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, tuple) and node[0] == "str":
        return [item if isinstance(item, str) else "" for item in node[1]]
    return []


def _attr(node, name: str):
    if not isinstance(node, tuple) or len(node) < 3:
        return None
    for tag, value in _pairs(node[2]):
        if tag == ("sym", name):
            return value
    return None


def rd_tag(node) -> str:
    texts = _strings(_attr(node, "Rd_tag"))
    return texts[0] if texts else ""


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


def _int_pair(node) -> tuple[int, int]:
    if isinstance(node, tuple) and node[0] == "int" and len(node[1]) >= 2:
        return int(node[1][0]), int(node[1][1])
    raise ValueError("help index entry is not an offset and a length")


def help_topics(package: str) -> list[tuple[str, object]]:
    folder = package_dir(package) / "help"
    base = folder / package
    index = parse_rds((base.with_suffix(".rdx")).read_bytes())
    variables = _component(index, "variables")
    if variables is None:
        raise LifecycleError(f"there is no package called \u2018{package}\u2019")
    compressed_node = _component(index, "compressed")
    compressed = True
    if isinstance(compressed_node, tuple) and compressed_node[0] == "int":
        compressed = bool(compressed_node[1] and compressed_node[1][0])
    raw = (base.with_suffix(".rdb")).read_bytes()
    names = _strings(_attr(variables, "names"))
    topics = []
    for name, entry in zip(names, variables[1]):
        offset, length = _int_pair(entry)
        chunk = raw[offset : offset + length]
        payload = chunk[4:]
        if compressed:
            payload = zlib.decompress(payload)
        topics.append((f"{name}.Rd", parse_rds(payload)))
    return topics


def _quote(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _element(node):
    if isinstance(node, str) or node is None:
        return node
    if not isinstance(node, tuple):
        return None
    if node[0] == "str":
        values = [item if isinstance(item, str) else None for item in node[1]]
        if len(values) == 1:
            return values[0]
        return ("c", values)
    if node[0] == "vec":
        return [_element(child) for child in node[1]]
    if node[0] == "sym":
        return node[1]
    return None


def _deparse(obj) -> str:
    if obj is None:
        return "NULL"
    if isinstance(obj, str):
        return _quote(obj)
    if isinstance(obj, tuple) and obj and obj[0] == "c":
        parts = ["NA" if item is None else _quote(item) for item in obj[1]]
        return "c(" + ", ".join(parts) + ")"
    if isinstance(obj, list):
        if not obj:
            return "list()"
        return "list(" + ", ".join(_deparse(item) for item in obj) + ")"
    return "NULL"


def _trim(text: str) -> str:
    return text.strip(" \t\r\n")


def description_text(topic) -> str:
    sections = []
    if not isinstance(topic, tuple) or topic[0] != "vec":
        return ""
    for child in topic[1]:
        if rd_tag(child) != "\\description":
            continue
        pieces = []
        for item in child[1]:
            value = _element(item)
            if isinstance(value, list) or (isinstance(value, tuple) and value and value[0] == "c"):
                pieces.append(_deparse(value))
            elif value is None:
                pieces.append("NA")
            else:
                pieces.append(value)
        sections.append(_trim("\n".join(pieces)))
    unique: list[str] = []
    for section in sections:
        if section not in unique:
            unique.append(section)
    return unique[0] if unique else ""


def lifecycle_token(topic):
    text = description_text(topic)
    if not text:
        return None
    found = _LIFECYCLE.search(text)
    if found is None:
        return None
    return found.group(1)


def _rd_piece(node) -> str:
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
    tag = rd_tag(node)
    if tag in _ZERO:
        return tag
    if tag == "COMMENT":
        return ""
    inner = "".join(_rd_piece(child) for child in node[1])
    if tag:
        return f"{tag}{{{inner}}}"
    return inner


def usage_text(topic) -> str:
    if not isinstance(topic, tuple) or topic[0] != "vec":
        return ""
    for child in topic[1]:
        if rd_tag(child) == "\\usage":
            text = "".join(_rd_piece(item) for item in child[1])
            text = text.replace("\\dots", "...").replace("\\ldots", "...")
            return text
    return ""


def usage_function_names(topic) -> list[str]:
    text = usage_text(topic)
    if not text.strip():
        return [""]
    names: list[str] = []
    i = 0
    n = len(text)
    depth = 0
    while i < n:
        char = text[i]
        if char in "\"'":
            quote = char
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if char == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if char == "(":
            depth += 1
            i += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0 and (char.isalpha() or char in "._"):
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "._"):
                j += 1
            if j < n and text[j] == "(":
                names.append(text[i:j])
            i = j
            continue
        i += 1
    return names or [""]


def match_which(which) -> list:
    if which is None:
        return list(_WHICH)
    if isinstance(which, str):
        which = [which]
    else:
        which = list(which)
    if not which:
        raise LifecycleError("'arg' must be of length >= 1")
    indexes = []
    for item in which:
        if item is None:
            indexes.append(0)
            continue
        if not isinstance(item, str):
            raise LifecycleError("'arg' must be NULL or a character vector")
        exact = [i for i, choice in enumerate(_WHICH, 1) if choice == item]
        if exact:
            indexes.append(exact[0])
            continue
        prefixes = [i for i, choice in enumerate(_WHICH, 1) if choice.startswith(item)]
        indexes.append(prefixes[0] if len(prefixes) == 1 else 0)
    if all(index == 0 for index in indexes):
        quoted = ", ".join(f"\u201c{choice}\u201d" for choice in _WHICH)
        raise LifecycleError(f"'arg' should be one of {quoted}")
    return [_WHICH[index - 1] for index in indexes if index > 0]
