"""Filesystem operations from fs 2.1.0.

Missing files are missing metadata. ``fail=False`` turns other stat and
directory errors into a warning instead of an exception.
"""

from __future__ import annotations

import ctypes
import errno
import grp
import os
import pwd
import shutil
import stat
import subprocess
import warnings
from datetime import datetime

from fs._error import FsError, assert_no_missing, assert_ok
from fs.bytes import FsBytes, fs_bytes
from fs.path import (
    FsPath,
    is_absolute_path,
    path,
    path_abs,
    path_dir,
    path_expand,
    path_file,
    path_filter,
    path_rel,
    path_split,
    path_tidy,
)
from fs.perms import FsPerms, fs_perms

_FILE_TYPES = (
    "block_device",
    "character_device",
    "directory",
    "FIFO",
    "symlink",
    "file",
    "socket",
)
_ENTRY_BITS = {
    "any": -1,
    "unknown": 1,
    "file": 2,
    "directory": 4,
    "symlink": 8,
    "FIFO": 16,
    "socket": 32,
    "character_device": 64,
    "block_device": 128,
}
_ACCESS = {"exists": 0, "read": os.R_OK, "write": os.W_OK, "execute": os.X_OK}
_UV_UNKNOWN, _UV_FILE, _UV_DIR, _UV_LINK = 0, 1, 2, 3
_UV_FIFO, _UV_SOCKET, _UV_CHAR, _UV_BLOCK = 4, 5, 6, 7


class FileInfo:
    """One column for each ``file_info`` field."""

    def __init__(self, columns: dict):
        self.columns = columns

    def __getitem__(self, key):
        return self.columns[key]

    def __len__(self) -> int:
        return len(self.columns["path"])


def _list(value):
    if isinstance(value, (list, tuple, FsPath)):
        return list(value)
    return [value]


def _info_type(mode: int):
    kind = stat.S_IFMT(mode)
    return {
        stat.S_IFBLK: 0,
        stat.S_IFCHR: 1,
        stat.S_IFDIR: 2,
        stat.S_IFIFO: 3,
        stat.S_IFLNK: 4,
        stat.S_IFREG: 5,
        stat.S_IFSOCK: 6,
    }.get(kind)


def _dirent_type(mode: int) -> int:
    kind = stat.S_IFMT(mode)
    return {
        stat.S_IFBLK: _UV_BLOCK,
        stat.S_IFCHR: _UV_CHAR,
        stat.S_IFDIR: _UV_DIR,
        stat.S_IFIFO: _UV_FIFO,
        stat.S_IFLNK: _UV_LINK,
        stat.S_IFREG: _UV_FILE,
        stat.S_IFSOCK: _UV_SOCKET,
    }.get(kind, _UV_UNKNOWN)


def _type_name(code) -> str | None:
    if code is None:
        return None
    if code < 0 or code >= len(_FILE_TYPES):
        return None
    return _FILE_TYPES[code]


def _owner(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def _group(gid: int) -> str:
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def _blank_row() -> dict:
    return {
        "device_id": None,
        "type": None,
        "permissions": None,
        "hard_links": None,
        "user": None,
        "group": None,
        "special_device_id": None,
        "inode": None,
        "size": None,
        "block_size": None,
        "blocks": None,
        "flags": None,
        "generation": None,
        "access_time": None,
        "modification_time": None,
        "change_time": None,
        "birth_time": None,
    }


_STATX = ctypes.create_string_buffer(512)
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.statx.restype = ctypes.c_int
_LIBC.statx.argtypes = (
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_uint,
    ctypes.c_void_p,
)


def _birth_time(text: str) -> float:
    """Birth time from statx. Zero when the filesystem does not record one."""
    result = _LIBC.statx(-100, os.fsencode(text), 0x100, 0x800, _STATX)
    if result != 0:
        return 0.0
    mask = int.from_bytes(_STATX.raw[0:4], "little")
    if not mask & 0x800:
        return 0.0
    seconds = int.from_bytes(_STATX.raw[80:88], "little", signed=True)
    nanos = int.from_bytes(_STATX.raw[88:92], "little")
    return seconds + nanos * 1e-9


def _stat_row(text: str, fail: bool) -> dict:
    try:
        info = os.lstat(text)
    except OSError as error:
        missing = error.errno in (errno.ENOENT, errno.ENOTDIR)
        if missing or not fail:
            if not missing:
                warnings.warn(f"Failed to stat '{text}': {error.strerror}", stacklevel=3)
            return _blank_row()
        raise FsError(f"Failed to stat '{text}': {error.strerror}") from error
    birth = _birth_time(text)
    return {
        "device_id": float(info.st_dev),
        "type": _info_type(info.st_mode),
        "permissions": int(info.st_mode),
        "hard_links": float(info.st_nlink),
        "user": _owner(info.st_uid),
        "group": _group(info.st_gid),
        "special_device_id": float(info.st_rdev),
        "inode": float(info.st_ino),
        "size": float(info.st_size),
        "block_size": float(getattr(info, "st_blksize", 0)),
        "blocks": float(getattr(info, "st_blocks", 0)),
        "flags": int(getattr(info, "st_flags", 0)),
        "generation": float(getattr(info, "st_gen", 0)),
        "access_time": float(info.st_atime),
        "modification_time": float(info.st_mtime),
        "change_time": float(info.st_ctime),
        "birth_time": float(birth),
    }


def link_path(paths) -> FsPath:
    """The stored target of a symbolic link."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    values = []
    for item in path_expand(incoming):
        try:
            values.append(os.readlink(item))
        except OSError as error:
            raise FsError(f"Failed to read link '{item}': {error.strerror}") from error
    return path_tidy(values)


def file_info(paths, fail: bool = True, follow: bool = False) -> FileInfo:
    """Metadata from ``lstat``. ``follow=True`` walks symbolic links."""
    incoming = _list(paths)
    rows = []
    for original, expanded in zip(incoming, path_expand(incoming)):
        if original is None or expanded is None:
            rows.append(_blank_row())
        else:
            rows.append(_stat_row(expanded, fail))
    info = _columns(path_tidy(incoming), rows)
    if follow:
        for index, kind in enumerate(info["type"]):
            while kind == "symlink":
                target = link_path(incoming[index])[0]
                if not is_absolute_path(target)[0]:
                    target = path(path_dir(incoming[index])[0], target)[0]
                followed = file_info(target, fail=fail, follow=False)
                for key, column in info.items():
                    column[index] = followed[key][0]
                incoming[index] = target
                kind = info["type"][index]
    return FileInfo(info)


def _columns(tidy: FsPath, rows: list[dict]) -> dict:
    keys = list(rows[0]) if rows else list(_blank_row())
    columns = {"path": list(tidy)}
    for key in (
        "type",
        "size",
        "permissions",
        "modification_time",
        "user",
        "group",
    ):
        columns[key] = [_cell(row, key) for row in rows]
    for key in keys:
        if key not in columns and key != "path":
            columns[key] = [_cell(row, key) for row in rows]
    columns["type"] = [_type_name(row["type"]) for row in rows]
    columns["size"] = FsBytes([None if row["size"] is None else float(row["size"]) for row in rows])
    columns["permissions"] = FsPerms(
        [None if row["permissions"] is None else int(row["permissions"]) for row in rows]
    )
    return columns


def _cell(row: dict, key: str):
    if key == "type":
        return _type_name(row["type"])
    return row[key]


def file_size(paths, fail: bool = True) -> FsBytes:
    info = file_info(paths, fail=fail)
    sized = FsBytes(list(info["size"]))
    sized.names = _list(paths)
    return sized


def _match_arg(values, choices: list[str]) -> list[str]:
    if isinstance(values, str):
        values = [values]
    picked = []
    for value in values:
        hits = [choice for choice in choices if choice.startswith(value)]
        assert_ok(len(hits) == 1, f"`type` must be one of {', '.join(choices)}")
        picked.append(hits[0])
    return picked


def file_access(paths, mode="exists") -> list[bool]:
    """True when ``path`` allows every requested access mode."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    selected = _match_arg(mode, list(_ACCESS))
    bits = 0
    for name in selected:
        bits |= _ACCESS[name]
    flags = []
    names = []
    for item in path_expand(incoming):
        names.append(item)
        flags.append(os.access(item, bits))
    return flags


def file_exists(paths) -> list[bool]:
    flags = []
    for item in path_expand(paths):
        if item is None:
            flags.append(False)
            continue
        try:
            os.stat(item)
            flags.append(True)
        except OSError:
            flags.append(False)
    return flags


def is_file(paths, follow: bool = True) -> list[bool]:
    info = file_info(paths, follow=follow)
    return [kind == "file" for kind in info["type"]]


def is_dir(paths, follow: bool = True) -> list[bool]:
    info = file_info(paths, follow=follow)
    return [kind == "directory" for kind in info["type"]]


def is_link(paths) -> list[bool]:
    info = file_info(paths)
    return [kind == "symlink" for kind in info["type"]]


def is_file_empty(paths, follow: bool = True) -> list[bool]:
    info = file_info(paths, follow=follow)
    return [size == 0 for size in info["size"]]


def dir_exists(paths) -> list[bool]:
    flags = is_dir(paths)
    links = is_link(paths)
    linked = [item for item, flag in zip(_list(paths), links) if flag]
    if linked:
        realized = []
        for item in linked:
            try:
                realized.append(is_dir(os.path.realpath(path_expand(item)[0]))[0])
            except OSError:
                realized.append(False)
        cursor = 0
        for index, flag in enumerate(links):
            if flag:
                flags[index] = realized[cursor]
                cursor += 1
    return [bool(flag) for flag in flags]


def link_exists(paths) -> list[bool]:
    return [bool(flag) for flag in is_link(paths)]


def is_dir_empty(paths) -> bool:
    return len(dir_ls(paths)) == 0


def _entry_type(entry: os.DirEntry, name: str, fail: bool) -> int:
    try:
        mode = entry.stat(follow_symlinks=False).st_mode
    except OSError as error:
        if not fail:
            warnings.warn(f"Failed to stat '{name}': {error.strerror}", stacklevel=4)
            return _UV_UNKNOWN
        raise FsError(f"Failed to stat '{name}': {error.strerror}") from error
    return _dirent_type(mode)


def _dir_map_one(folder: str, fun, all_: bool, type_mask: int, recurse: int, fail: bool) -> list:
    if recurse < 0:
        recurse = 2**31 - 1
    try:
        entries = list(os.scandir(folder))
        entries.sort(key=lambda entry: os.fsencode(entry.name))
    except OSError as error:
        if not fail:
            warnings.warn(f"Failed to search directory '{folder}': {error.strerror}", stacklevel=3)
            return []
        raise FsError(f"Failed to search directory '{folder}': {error.strerror}") from error
    found = []
    for entry in entries:
        if not all_ and entry.name.startswith("."):
            continue
        if folder == ".":
            name = entry.name
        elif folder.endswith("/"):
            name = folder + entry.name
        else:
            name = folder + "/" + entry.name
        kind = _entry_type(entry, name, fail)
        if type_mask == -1 or ((1 << kind) & type_mask) > 0:
            found.append(fun(name))
        if recurse > 0 and kind == _UV_DIR:
            found.extend(_dir_map_one(name, fun, all_, type_mask, recurse - 1, fail))
    return found


def dir_map(paths=".", fun=None, all: bool = False, recurse=False, type="any", fail: bool = True):
    """Apply ``fun`` to each directory entry and return the results."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    assert_ok(fun is not None, "`fun` must be a function")
    if isinstance(recurse, bool):
        recurse = -1 if recurse else 0
    chosen = _match_arg(type, list(_ENTRY_BITS))
    mask = sum(_ENTRY_BITS[name] for name in chosen)
    results = []
    for item in path_expand(incoming):
        results.extend(_dir_map_one(item, fun, all, mask, int(recurse), fail))
    return results


def dir_ls(
    paths=".",
    all: bool = False,
    recurse=False,
    type="any",
    glob=None,
    regexp=None,
    invert: bool = False,
    fail: bool = True,
    recursive=None,
) -> FsPath:
    """List directory entries. ``recursive`` is the old name of ``recurse``."""
    if recursive is not None:
        warnings.warn("`recursive` is deprecated, please use `recurse` instead", stacklevel=2)
        recurse = recursive
    files = [str(item) for item in dir_map(paths, lambda name: name, all, recurse, type, fail)]
    return path_filter(files, glob, regexp, invert)


def dir_walk(paths=".", fun=None, all: bool = False, recurse=False, type="any", fail: bool = True) -> FsPath:
    """Call ``fun`` for each entry and return ``paths``."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    dir_map(path_expand(incoming), fun, all, recurse, type, fail)
    return path_tidy(incoming)


def dir_info(
    paths=".",
    all: bool = False,
    recurse=False,
    type="any",
    regexp=None,
    glob=None,
    fail: bool = True,
) -> FileInfo:
    """``file_info`` of ``dir_ls``."""
    return file_info(
        dir_ls(paths, all=all, recurse=recurse, type=type, regexp=regexp, glob=glob, fail=fail),
        fail=fail,
    )


def file_create(paths, *parts, mode: str = "u=rw,go=r") -> FsPath:
    """Create an empty file. An existing file is left as it is."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    assert_ok(isinstance(mode, str) or len(_list(mode)) == 1, "`mode` must be of length 1")
    bits = int(fs_perms(mode)[0]) & 0xFFFF
    created = path_expand(path(incoming, *parts) if parts else incoming)
    for item in created:
        try:
            fd = os.open(item, os.O_CREAT | os.O_WRONLY, bits)
            os.close(fd)
        except OSError as error:
            raise FsError(f"Failed to open '{item}': {error.strerror}") from error
    return path_tidy(created)


def dir_create(paths, *parts, mode: str = "u=rwx,go=rx", recurse: bool = True, recursive=None) -> FsPath:
    """Create a directory. An existing directory is left as it is."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    assert_ok(isinstance(mode, str) or len(_list(mode)) == 1, "`mode` must be of length 1")
    if recursive is not None:
        warnings.warn("`recursive` is deprecated, please use `recurse` instead", stacklevel=2)
        recurse = recursive
    bits = int(fs_perms(mode)[0]) & 0xFFFF
    created = list(path_expand(path(incoming, *parts) if parts else incoming))
    if not recurse:
        for item in created:
            _mkdir(item, bits)
        return path_tidy(created)
    for pieces in path_split(created):
        if len(pieces) <= 1:
            _mkdir(path(*pieces)[0] if pieces else created[0], bits)
            continue
        accumulated = []
        built = []
        for piece in pieces:
            accumulated.append(piece)
            built.append(path(*accumulated)[0])
        if pieces and is_absolute_path(pieces[0])[0]:
            built = built[1:]
        for item in built:
            _mkdir(item, bits)
    return path_tidy(created)


def _mkdir(folder: str, bits: int) -> None:
    try:
        os.mkdir(folder, 0o777)
    except FileExistsError:
        if os.path.isdir(folder) or os.path.islink(folder):
            return
        raise FsError(f"Failed to make directory '{folder}'") from None
    except PermissionError:
        return
    except OSError as error:
        raise FsError(f"Failed to make directory '{folder}': {error.strerror}") from error
    try:
        os.chmod(folder, bits)
    except OSError as error:
        raise FsError(f"Failed to set permissions for directory '{folder}': {error.strerror}") from error


def link_create(paths, new_path, symbolic: bool = True) -> FsPath:
    """Create a symbolic link, or a hard link when ``symbolic`` is false."""
    sources = list(path_tidy(paths))
    targets = list(path_tidy(new_path))
    assert_no_missing(sources, "path")
    assert_no_missing(targets, "new_path")
    assert_ok(len(sources) == len(targets), "Length of `path` must equal length of `new_path`")
    for source, target in zip(path_expand(sources), path_expand(targets)):
        try:
            if symbolic:
                os.symlink(source, target)
            else:
                os.link(source, target)
        except OSError as error:
            raise FsError(f"Failed to create link '{target}': {error.strerror}") from error
    return path_tidy(targets)


def _unlink(items: list[str]) -> None:
    for item in items:
        try:
            os.unlink(item)
        except OSError as error:
            raise FsError(f"Failed to remove '{item}': {error.strerror}") from error


def dir_delete(paths) -> FsPath:
    """Delete a directory and everything under it."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    expanded = list(path_expand(incoming))
    directories = dir_ls(expanded, type="directory", recurse=True, all=True)
    files = dir_ls(
        expanded,
        type=["unknown", "file", "symlink", "FIFO", "socket", "character_device", "block_device"],
        recurse=True,
        all=True,
    )
    _unlink([str(item) for item in files])
    for item in reversed([*expanded, *[str(entry) for entry in directories]]):
        try:
            os.rmdir(item)
        except OSError as error:
            raise FsError(f"Failed to remove '{item}': {error.strerror}") from error
    return path_tidy(incoming)


def file_delete(paths) -> FsPath:
    """Delete files. Directories are passed to ``dir_delete``."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    expanded = list(path_expand(incoming))
    directories = [item for item, flag in zip(expanded, is_dir(expanded)) if flag]
    if directories:
        dir_delete(directories)
    others = [item for item, flag in zip(expanded, is_dir(expanded)) if not flag]
    _unlink(others)
    return path_tidy(incoming)


def link_delete(paths) -> FsPath:
    """Delete symbolic links."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    assert_ok(all(is_link(incoming)), "`path` must be a link")
    _unlink(list(path_expand(incoming)))
    return path_tidy(incoming)


def _into_directory(sources: list[str], targets: list[str]) -> list[str]:
    exists = file_exists(targets)
    directories = [flag and kind for flag, kind in zip(exists, is_dir(targets))]
    if len(targets) == 1 and directories[0]:
        targets = targets * len(sources)
        directories = directories * len(sources)
    assert_ok(len(sources) == len(targets), "Length of `path` must equal length of `new_path`")
    moved = []
    for source, target, is_directory in zip(sources, targets, directories):
        if is_directory:
            moved.append(path(target, os.path.basename(source))[0])
        else:
            moved.append(target)
    return moved


def file_copy(paths, new_path, overwrite: bool = False) -> FsPath:
    """Copy file contents. Existing files are refused unless ``overwrite`` is true."""
    sources = list(path_expand(path_tidy(paths)))
    targets = list(path_expand(path_tidy(new_path)))
    assert_no_missing(sources, "path")
    assert_no_missing(targets, "new_path")
    targets = _into_directory(sources, targets)
    for source, target in zip(sources, targets):
        if not overwrite and os.path.exists(target):
            raise FsError(f"Failed to copy '{source}' to '{target}': File exists")
        try:
            shutil.copyfile(source, target)
        except OSError as error:
            raise FsError(f"Failed to copy '{source}' to '{target}': {error.strerror}") from error
    return path_tidy(targets)


def link_copy(paths, new_path, overwrite: bool = False) -> FsPath:
    """Copy a symbolic link, not the file it points at."""
    sources = list(path_tidy(paths))
    targets = list(path_tidy(new_path))
    assert_no_missing(sources, "path")
    assert_no_missing(targets, "new_path")
    assert_ok(all(is_link(sources)), "`path` must be a link")
    expanded_new = list(path_expand(targets))
    for target, exists in zip(expanded_new, link_exists(expanded_new)):
        if overwrite and exists:
            link_delete(target)
    return link_create(link_path(path_expand(sources)), expanded_new)


def dir_copy(paths, new_path, overwrite: bool = False) -> FsPath:
    """Copy a directory tree, including its symbolic links."""
    sources = list(path_tidy(paths))
    targets = list(path_tidy(new_path))
    assert_no_missing(sources, "path")
    assert_no_missing(targets, "new_path")
    assert_ok(all(is_dir(sources)), "`path` must be a directory")
    assert_ok(len(sources) == len(targets), "Length of `path` must equal length of `new_path`")
    for index, source in enumerate(sources):
        if not overwrite and is_dir(targets[index])[0]:
            targets[index] = path(targets[index], path_file(sources))[0]
        dir_create(targets[index])
        directories = dir_ls(source, type="directory", recurse=True, all=True)
        if directories:
            dir_create(path(targets[index], path_rel(directories, source)))
        files = dir_ls(
            source,
            recurse=True,
            type=["unknown", "file", "FIFO", "socket", "character_device", "block_device"],
            all=True,
        )
        if files:
            file_copy(files, path(targets[index], path_rel(files, source)), overwrite=overwrite)
        links = dir_ls(source, recurse=True, type="symlink", all=True)
        if links:
            link_copy(links, path(targets[index], path_rel(links, source)), overwrite=overwrite)
    return path_tidy(targets)


def file_move(paths, new_path) -> FsPath:
    """Rename files. A directory destination receives the files inside it."""
    sources = list(path_expand(path_tidy(paths)))
    targets = list(path_expand(path_tidy(new_path)))
    assert_no_missing(sources, "path")
    assert_no_missing(targets, "new_path")
    targets = _into_directory(sources, targets)
    for source, target in zip(sources, targets):
        try:
            os.rename(source, target)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise FsError(f"Failed to move '{source}' to '{target}': {error.strerror}") from error
            shutil.copyfile(source, target)
            os.unlink(source)
    return path_tidy(targets)


def file_chmod(paths, mode) -> FsPath:
    """Change permissions. A symbolic mode is applied to the current mode."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    current = file_info(incoming)["permissions"]
    updated = fs_perms(mode, mode=list(current))
    for item, bits in zip(path_expand(incoming), updated):
        try:
            os.chmod(item, int(bits) & 0xFFFF)
        except OSError as error:
            raise FsError(f"Failed to chmod '{item}': {error.strerror}") from error
    return path_tidy(incoming)


def _id(value, kind: str) -> int:
    if value is None:
        return -1
    if isinstance(value, str):
        try:
            if kind == "user":
                return pwd.getpwnam(value).pw_uid
            return grp.getgrnam(value).gr_gid
        except KeyError:
            return -1
    return int(value)


def file_chown(paths, user_id=None, group_id=None) -> FsPath:
    """Change owner and group. ``None`` leaves that id unchanged."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    uid = _id(user_id, "user")
    gid = _id(group_id, "group")
    for item in path_expand(incoming):
        try:
            os.chown(item, uid, gid)
        except OSError as error:
            raise FsError(f"Failed to chown '{item}': {error.strerror}") from error
    return path_tidy(incoming)


def _posix_time(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        return value.timestamp()
    text = str(value)
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return datetime.strptime(text, "%Y-%m-%d").timestamp()


def file_touch(paths, access_time=None, modification_time=None) -> FsPath:
    """Set access and modification times, creating the file when needed."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    if access_time is None:
        access_time = datetime.now().timestamp()
    else:
        access_time = _posix_time(access_time)
    if modification_time is None:
        modification_time = access_time
    else:
        modification_time = _posix_time(modification_time)
    expanded = list(path_expand(incoming))
    for item in expanded:
        fd = os.open(item, os.O_CREAT | os.O_WRONLY, 0o644)
        os.close(fd)
        os.utime(item, (access_time, modification_time))
    return path_tidy(expanded)


def file_show(paths=".", browser=None) -> FsPath:
    """Open each path with ``browser``, or with ``xdg-open`` when it is omitted."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    command = browser or os.environ.get("BROWSER") or "xdg-open"
    for item in path_expand(incoming):
        if callable(command):
            command(item)
        else:
            subprocess.Popen([command, item], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path_tidy(incoming)


def _box(horizontal: str, vertical: str, last: str, join: str) -> dict:
    return {"h": horizontal, "v": vertical, "l": last, "j": join}


def dir_tree(paths=".", recurse: bool = True, **options) -> FsPath:
    """Print a directory tree and return the entries that were listed."""
    root = _list(paths)[0]
    files = list(dir_ls(root, recurse=recurse, **options))

    def ancestors(item: str) -> list[str]:
        pieces = path_split(item)[0]
        built = []
        acc = []
        for piece in pieces:
            acc.append(piece)
            built.append(path(*acc)[0])
        return built

    extra = []
    for item in files:
        extra.extend(ancestors(path_dir([item])[0]))
    extra = [item for item in extra if item != root]
    ordered = []
    for item in [*files, *extra]:
        if item not in ordered:
            ordered.append(item)
    by_dir: dict[str, list[str]] = {}
    for item in ordered:
        by_dir.setdefault(path_dir([item])[0], []).append(item)
    drawing = _box("─", "│", "└", "├")
    print(root)

    def leaves(folder: str, indent: str) -> None:
        children = by_dir.get(folder, [])
        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = drawing["l"] if last else drawing["j"]
            line = drawing["h"] + drawing["h"]
            print(f"{indent}{branch}{line} {path_file([child])[0]}")
            deeper = indent + ("    " if last else drawing["v"] + "   ")
            leaves(child, deeper)

    leaves(path_expand(root)[0], "")
    return FsPath(files)
