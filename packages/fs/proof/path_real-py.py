
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

    return path_real("/etc/passwd")

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
