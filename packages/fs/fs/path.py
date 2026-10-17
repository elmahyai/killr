"""Path computations from fs 2.1.0.

``path_real`` touches the filesystem. The other functions only rewrite strings.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence

from fs._error import FsError, assert_ok, assert_recyclable

_EXT_TAIL = re.compile(r"[.]+([^.]+)$")


class FsPath(list):
    """A character vector of tidy paths."""

    def __str__(self) -> str:
        if not self:
            return "character(0)"
        return " ".join("NA" if item is None else item for item in self)


def _as_list(path) -> list:
    if path is None:
        return [None]
    if isinstance(path, FsPath):
        return list(path)
    if isinstance(path, (list, tuple)):
        return [_one(item) for item in path]
    return [_one(path)]


def _one(value):
    if value is None:
        return None
    return str(value)


def _box(values: list) -> FsPath:
    return FsPath(values)


def path_tidy(path) -> FsPath:
    """Turn separators into ``/`` and drop repeated and trailing slashes."""
    return _box([_tidy_one(item) for item in _as_list(path)])


def _tidy_one(path):
    if path is None:
        return None
    out: list[str] = []
    previous = "\0"
    index = 0
    text = str(path)
    size = len(text)
    while index < size:
        current = text[index]
        index += 1
        if current == "\\":
            current = "/"
        if index > 2 and previous == "/" and current == "/":
            while index < size and previous == "/" and current == "/":
                previous = current
                current = text[index]
                index += 1
            if index == size and current == "/":
                break
        previous = current
        out.append(previous)
    tidy = "".join(out)
    if _is_windows_drive(tidy):
        tidy = tidy[0].upper() + tidy[1:]
        if len(tidy) == 2:
            tidy += "/"
        elif len(tidy) > 3 and tidy.endswith("/"):
            tidy = tidy[:-1]
        return tidy
    if len(tidy) > 1 and tidy.endswith("/"):
        tidy = tidy[:-1]
    return tidy


def _is_windows_drive(text: str) -> bool:
    return (
        len(text) >= 2
        and text[0].isalpha()
        and text[1] == ":"
    )


def is_absolute_path(path) -> list[bool]:
    """True for ``~``, a leading slash, or a Windows drive."""
    raw = _as_list(path)
    tidy = path_tidy(raw)
    result = []
    for original, cleaned in zip(raw, tidy):
        if original is None or cleaned is None:
            result.append(False)
            continue
        lead = bool(re.match(r"^~", str(original)))
        rooted = bool(re.match(r"^(/+|[A-Za-z]:)", cleaned))
        result.append(lead or rooted)
    return result


def _recycle(columns: list[list], ext: list) -> list[list]:
    lengths = [len(column) for column in columns] + [len(ext)]
    assert_recyclable(lengths)
    if any(length == 0 for length in lengths):
        return []
    rows = max(lengths)
    built = []
    for row in range(rows):
        pieces = []
        missing = False
        for column in columns:
            piece = column[row % len(column)]
            if piece is None:
                missing = True
                break
            pieces.append(piece)
        extension = ext[row % len(ext)]
        if extension is None:
            missing = True
        built.append(None if missing else (pieces, extension))
    return built


def _join_pieces(pieces: list[str], extension: str) -> str:
    parts: list[str] = []
    for index, piece in enumerate(pieces):
        parts.append(piece)
        trailing = piece.endswith("/") or piece.endswith("\\")
        if not trailing and index != len(pieces) - 1:
            parts.append("/")
    if extension:
        parts.append("." + extension)
    return _tidy_one("".join(parts))


def path(*parts, ext: str | Sequence | None = "") -> FsPath:
    """Join path components. Only arguments of length one are recycled."""
    if not parts:
        return FsPath()
    columns = [_as_list(part) for part in parts]
    extensions = _as_list(ext)
    rows = _recycle(columns, extensions)
    values = []
    for row in rows:
        if row is None:
            values.append(None)
        else:
            values.append(_join_pieces(row[0], "" if row[1] is None else str(row[1])))
    return _box(values)


def path_wd(*parts, ext="") -> FsPath:
    """Join components onto the working directory."""
    return path(os.getcwd(), *parts, ext=ext)


def path_split(path) -> list[list[str]]:
    """Split a tidy path. A root is ``/`` and a UNC root keeps its host."""
    parts = []
    for item in path_tidy(path):
        if item is None:
            parts.append([None])
            continue
        if item == "":
            parts.append([])
            continue
        parts.append(_split_one(item))
    return parts


def _split_one(text: str) -> list[str]:
    if text.startswith("//"):
        rest = text[2:]
        slash = rest.find("/")
        if slash == -1:
            return [text]
        head = "//" + rest[:slash]
        tail = rest[slash + 1 :]
        return [head, *tail.split("/")] if tail else [head]
    if text.startswith("/"):
        rest = text[1:]
        return ["/"] if rest == "" else ["/", *rest.split("/")]
    return text.split("/")


def path_join(parts) -> FsPath:
    """Join split components. A list of vectors is joined one vector at a time."""
    if isinstance(parts, (str, FsPath)) or (
        isinstance(parts, (list, tuple)) and parts and not isinstance(parts[0], (list, tuple))
    ):
        if not isinstance(parts, (list, tuple, FsPath)):
            parts = [parts]
        if len(parts) == 0:
            return path_tidy("")
        return path(*[_one(part) for part in parts])
    if len(parts) == 0:
        return path_tidy("")
    return _box([path_join(part)[0] if part else "" for part in parts])


def path_norm(path) -> FsPath:
    """Drop ``.`` and collapse ``..`` without resolving symbolic links."""
    incoming = _as_list(path)
    split = path_split(incoming)
    values = []
    for original, pieces in zip(incoming, split):
        if original is None:
            values.append(None)
            continue
        values.append(_norm_one(pieces))
    return path_tidy(values)


def _norm_one(pieces: list[str]) -> str:
    pieces = [piece for piece in pieces if piece != "."]
    if any(piece == ".." for piece in pieces):
        absolute = bool(pieces) and is_absolute_path(pieces[0])[0]
        first = pieces[0] if pieces else ""
        kept: list[str] = []
        for piece in pieces:
            if (
                piece != ".."
                or (not absolute and not kept)
                or (kept and kept[-1] == "..")
            ):
                kept.append(piece)
            elif kept:
                kept.pop()
        if absolute and (not kept or kept[0] != first):
            kept = [first, *kept]
        pieces = kept
    if not pieces:
        return "."
    return path_join(pieces)[0]


def path_abs(paths, start=".") -> FsPath:
    """Return an absolute normalized path. ``start`` anchors relative paths."""
    incoming = _as_list(paths)
    anchor = _as_list(start)
    if len(anchor) != 1:
        anchor = anchor[:1] if anchor else ["."]
    base = anchor[0]
    if base is None or not is_absolute_path(base)[0]:
        base = path_norm(path(os.getcwd(), "." if base is None else base))[0]
    absolute = is_absolute_path(incoming)
    values = []
    for item, is_abs in zip(incoming, absolute):
        if item is None:
            values.append(None)
        elif is_abs:
            values.append(path_norm(item)[0])
        else:
            values.append(path_norm(path(base, item))[0])
    return path_tidy(values)


def _home_directory() -> str:
    override = os.environ.get("R_FS_HOME", "")
    if override:
        return _tidy_one(override) or ""
    profile = os.environ.get("USERPROFILE", "")
    if profile:
        return _tidy_one(profile) or ""
    drive = os.environ.get("HOMEDRIVE", "")
    path_part = os.environ.get("HOMEPATH", "")
    if drive or path_part:
        return _tidy_one(drive + path_part) or ""
    return os.path.expanduser("~")


def _expand_windows(text: str) -> str:
    if text == "" or not text.startswith("~"):
        return text
    split_at = len(text)
    for index, char in enumerate(text):
        if char in "/\\":
            split_at = index
            break
    home = _home_directory()
    if split_at != 1:
        parent = os.path.dirname(home.rstrip("/"))
        if parent == "":
            parent = "/"
        user = text[:split_at]
        home = parent.rstrip("/") + "/" + user[1:]
    if len(text) > split_at:
        rest = text[split_at:]
        if not home.endswith("/"):
            home += "/"
        home = home.rstrip("/") + "/" + rest.lstrip("/\\")
    return home


def _expand_unix(text: str) -> str:
    if text is None:
        return None
    if "~" not in text:
        return text
    return os.path.expanduser(text)


def path_expand(path) -> FsPath:
    """Expand ``~`` and ``~user``. ``R_FS_HOME`` selects the Windows rule."""
    windows = os.environ.get("R_FS_HOME", "") != "" or os.name == "nt"
    values = []
    for item in _as_list(path):
        if item is None:
            values.append(None)
        elif windows:
            values.append(_expand_windows(str(item)))
        else:
            values.append(_expand_unix(str(item)))
    return path_tidy(values)


def path_expand_r(path) -> FsPath:
    """Expand ``~`` with the platform home directory, ignoring ``R_FS_HOME``."""
    values = []
    for item in _as_list(path):
        values.append(None if item is None else _expand_unix(str(item)))
    return path_tidy(values)


def path_home(*parts) -> FsPath:
    return path(path_expand("~/"), *parts)


def path_home_r(*parts) -> FsPath:
    return path(path_expand_r("~/"), *parts)


def path_real(path) -> FsPath:
    """Canonical path. The file must exist."""
    expanded = path_expand(path)
    values = []
    for item in expanded:
        if item is None:
            values.append(None)
            continue
        try:
            values.append(os.path.realpath(item))
        except OSError as error:
            raise FsError(f"Failed to realize '{item}': {error.strerror}") from error
    return path_tidy(values)


def _r_basename(text: str) -> str:
    if text in ("", ".", ".."):
        return text
    return os.path.basename(text.rstrip("/")) or os.path.basename(text)


def _r_dirname(text: str) -> str:
    if text in ("", "."):
        return "."
    parent = os.path.dirname(text)
    return "." if parent == "" else parent


def path_file(path) -> list:
    """Filename portion. Missing values stay missing."""
    values = []
    for item in _as_list(path):
        values.append(None if item is None else _r_basename(str(item)))
    return values


def path_dir(path) -> list:
    """Directory portion, tidied. A bare filename is ``.``."""
    values = []
    for item in _as_list(path):
        if item is None:
            values.append(None)
        else:
            values.append(_tidy_one(_r_dirname(str(item))))
    return values


def _extension_match(name: str):
    match = _EXT_TAIL.search(name)
    if match is None:
        return None
    start = match.start()
    if start == 0:
        return None
    return match


def _capture_extension(name: str) -> str:
    match = _extension_match(name)
    if match is None or name[match.start() - 1] in "./":
        return ""
    return match.group(1)


def _strip_extension(name: str) -> str:
    match = _extension_match(name)
    if match is None or name[match.start() - 1] == ".":
        return name
    return name[: match.start()]


def path_ext(path) -> list:
    """Last extension, without the dot. A name with no extension is empty."""
    names = path_file(path)
    values = []
    for original, name in zip(_as_list(path), names):
        if original is None or name is None:
            values.append(None)
            continue
        values.append(_capture_extension(name))
    return values


def path_ext_remove(paths) -> list:
    """Drop the last extension."""
    incoming = _as_list(paths)
    directories = path_dir(incoming)
    files = []
    for item in path_file(incoming):
        if item is None:
            files.append(None)
        else:
            files.append(_strip_extension(item))
    values = []
    for original, directory, file_name in zip(incoming, directories, files):
        if original is None:
            values.append(None)
            continue
        no_dir = directory in (".", "", None)
        if no_dir:
            values.append(_tidy_one(file_name))
        else:
            values.append(path(directory, file_name)[0])
    return values


def path_ext_set(path, ext) -> FsPath:
    """Replace the last extension. A leading dot on ``ext`` is removed."""
    incoming = _as_list(path)
    extensions = _as_list(ext)
    if not (len(extensions) == len(incoming) or len(extensions) == 1):
        assert_recyclable([len(incoming), len(extensions)])
    cleaned = []
    for item in extensions:
        if item is None:
            cleaned.append(None)
        else:
            cleaned.append(re.sub(r"^[.]", "", str(item)))
    if len(cleaned) == 1 and len(incoming) != 1:
        cleaned = cleaned * len(incoming)
    stripped = path_ext_remove(incoming)
    values = []
    for original, base, extension in zip(incoming, stripped, cleaned):
        if original is None or not extension:
            values.append(original if original is None else _tidy_one(str(original)))
            continue
        values.append(f"{base}.{extension}")
    return path_tidy(values)


def path_ext_replace(path, value) -> FsPath:
    """``path_ext<-``. Same replacement as ``path_ext_set``."""
    return path_ext_set(path, value)


def path_common(path) -> FsPath:
    """Longest shared prefix. Every path must be absolute, or every path relative."""
    incoming = _as_list(path)
    if any(item is None for item in incoming):
        return path_tidy(None)
    flags = is_absolute_path(incoming)
    if not (all(flags) or not any(flags)):
        raise FsError("Can't mix absolute and relative paths")
    normalized = sorted(str(item) for item in path_norm(incoming))
    pieces = []
    for item in normalized:
        pieces.append([part for part in path_split(item)[0] if part != "."])
    first, last = pieces[0], pieces[-1]
    common = list(first)
    for index, (left, right) in enumerate(zip(first, last)):
        if left != right:
            common = [] if index == 0 else first[:index]
            break
    else:
        if len(first) > len(last):
            common = list(last)
    if common == [""]:
        return path_tidy("")
    return path_join(common)


def path_rel(path, start=".") -> FsPath:
    """Path relative to ``start``. ``start`` must be one path."""
    anchor = _as_list(start)
    assert_ok(len(anchor) <= 1, "`start` must be a single path to a starting directory.")
    if len(anchor) == 0:
        raise FsError("`start` must be a single path to a starting directory.")
    start_abs = path_abs(path_expand(anchor[0]))[0]
    incoming = path_abs(path_expand(path))
    if start_abs is None:
        return path_tidy([None] * len(incoming))
    start_parts = path_split(start_abs)[0]
    values = []
    for item in incoming:
        if item is None:
            values.append(None)
            continue
        common = path_common([start_abs, item])[0]
        shared = len(path_split(common)[0]) if common else 0
        item_parts = path_split(item)[0]
        climb = [".."] * (len(start_parts) - shared)
        rest = item_parts[shared:]
        relative = climb + rest
        values.append("." if not relative else path_join(relative)[0])
    return path_tidy(values)


def _glob2rx(pattern: str) -> str:
    escaped = re.sub(r"\.", r"\\.", pattern)
    escaped = escaped.replace("?", ".").replace("*", ".*")
    return "^" + escaped + "$"


def path_filter(path, glob=None, regexp=None, invert=False) -> FsPath:
    """Keep paths matching a glob or a regular expression. Names are the inputs."""
    if glob is not None and regexp is not None:
        raise FsError("`glob` and `regexp` cannot both be set.")
    incoming = _as_list(path)
    pattern = _glob2rx(glob) if glob is not None else regexp
    if pattern is None:
        result = path_tidy(incoming)
        result.names = ["" if item is None else str(item) for item in incoming]
        return result
    compiled = re.compile(pattern)
    kept_raw = []
    for item in incoming:
        text = "" if item is None else str(item)
        matched = compiled.search(text) is not None
        if matched != bool(invert):
            kept_raw.append(item)
    result = path_tidy(kept_raw)
    result.names = ["" if item is None else str(item) for item in kept_raw]
    return result


def path_has_parent(path, parent) -> list[bool]:
    """True when ``parent`` is the path or one of its parents."""
    paths = path_expand(path_abs(path))
    parents = path_expand(path_abs(parent))
    assert_recyclable([len(paths), len(parents)])
    if len(paths) == 1:
        paths = FsPath(list(paths) * len(parents))
    if len(parents) == 1:
        parents = FsPath(list(parents) * len(paths))
    flags = []
    for item, owner in zip(paths, parents):
        if item is None or owner is None:
            flags.append(False)
            continue
        shared = path_common([item, owner])[0]
        flags.append(shared == owner)
    return flags


def path_sanitize(filename, replacement="") -> list[str]:
    """Drop characters that are unsafe in a filename, then limit it to 255 bytes."""
    illegal = re.compile(r'[/\\?<>:*|":]')
    control = re.compile(r"[\x00-\x1f\x7f]")
    reserved = re.compile(r"^[.]+$")
    windows_reserved = re.compile(
        r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])([.].*)?$",
        re.IGNORECASE,
    )
    trailing = re.compile(r"[. ]+$")
    values = []
    for item in _as_list(filename):
        if item is None:
            values.append(None)
            continue
        text = str(item)
        text = illegal.sub(replacement, text)
        text = control.sub(replacement, text)
        text = reserved.sub(replacement, text)
        text = windows_reserved.sub(replacement, text)
        text = trailing.sub(replacement, text)
        text = text.encode("utf-8")[:255].decode("utf-8", errors="ignore")
        values.append(text)
    if replacement == "":
        return values
    return path_sanitize(values, "")


def path_select_components(path, index, from_="start") -> FsPath:
    """Keep path components by position. ``from_`` is ``start`` or ``end``."""
    if from_ not in ("start", "end"):
        raise FsError("`from` must be one of 'start', 'end'")
    if isinstance(index, int):
        indexes = [index]
    else:
        indexes = list(index)
    selected = []
    for pieces in path_split(path):
        if pieces == [None]:
            selected.append(None)
            continue
        if indexes and max(abs(item) for item in indexes) > len(pieces):
            raise FsError("`seq` contains a higher number than the path has components.")
        if from_ == "start":
            chosen = _r_subset(pieces, indexes)
        else:
            order = list(range(len(pieces)))
            chosen_order = _r_subset(list(reversed(order)), indexes)
            chosen_order = list(reversed(chosen_order))
            chosen = [pieces[position] for position in chosen_order]
        selected.append(path_join(chosen)[0] if chosen else path_join([])[0])
    return FsPath(selected)


def _r_subset(values: list, index: list[int]) -> list:
    """R's ``[`` for a positive or negative index, 1-based."""
    if not index:
        return []
    if any(item == 0 for item in index):
        raise FsError("0 is not a valid component index")
    if all(item > 0 for item in index):
        return [values[item - 1] for item in index]
    if all(item < 0 for item in index):
        banned = {-item for item in index}
        return [value for number, value in enumerate(values, start=1) if number not in banned]
    raise FsError("only 0's may be mixed with negative subscripts")


def fs_path(x) -> FsPath:
    """Coerce ``x`` to a tidy path vector. ``None`` is an empty vector."""
    if x is None:
        return FsPath()
    return path_tidy(x)


as_fs_path = fs_path


def divide_paths(left, right) -> FsPath:
    """``/`` for two path vectors. This is ``path(left, right)``."""
    return path(left, right)


def add_paths(left, right) -> FsPath:
    """``+`` concatenates the strings and tidies the result."""
    lefts = _as_list(left)
    rights = _as_list(right)
    assert_recyclable([len(lefts), len(rights)])
    rows = max(len(lefts), len(rights))
    values = []
    for row in range(rows):
        one = lefts[row % len(lefts)]
        two = rights[row % len(rights)]
        if one is None or two is None:
            values.append(None)
        else:
            values.append(str(one) + str(two))
    return FsPath(values)
