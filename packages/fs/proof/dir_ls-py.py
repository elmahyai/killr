
import contextlib
import getpass
import io
import json
import os
import statistics
import tempfile
import time

from fs import *
from fs.perms import format_fs_perms

def one():

    root = tempfile.mkdtemp(prefix="fsproof-")
    dir_create(root)
    dir_create(path(root, "d/sub"))
    file_create(path(root, ["d/a.txt", "d/sub/b.txt"]))
    link_create(path_abs(path(root, "d/a.txt")), path(root, "d/link"))

    return path_rel(dir_ls(path(root, "d"), recurse=True), path(root, "d"))

def _atom(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)

def _emit(value):
    if isinstance(value, (list, tuple, FsPath, FsBytes, FsPerms)):
        return [
            _emit(item) if isinstance(item, (list, tuple, FsPath, FsBytes, FsPerms)) else _atom(item)
            for item in value
        ]
    return [_atom(value)]

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": _emit(value), "median_ms": statistics.median(elapsed)}))
