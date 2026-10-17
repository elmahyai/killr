"""checkMD5sums from tools 4.5.0."""

from __future__ import annotations

import os
import re
import sys
from typing import Any

from tools.checksum import md5sum


def _quote(name: str) -> str:
    return f"\u2018{name}\u2019"


def _files_under(directory: str) -> list[str]:
    found = []
    for folder, _dirs, files in os.walk(directory):
        for name in files:
            found.append(os.path.relpath(os.path.join(folder, name), directory))
    return sorted(found)


def check_md5sums(package: str | None = None, directory: str | None = None) -> Any:
    """True when every MD5 line matches a file under directory. NA when there is no MD5."""
    if directory is None:
        if package is None:
            raise ValueError("either package or dir is required")
        return None
    if isinstance(directory, (list, tuple)):
        if len(directory) != 1:
            return None
        directory = directory[0]
    md5file = os.path.join(directory, "MD5")
    if not os.path.exists(md5file):
        return None
    lines = open(md5file, encoding="utf-8").read().splitlines()
    recorded = {}
    order = []
    for line in lines:
        digest = re.sub(r"^([0-9a-fA-F]*)(.*)", r"\1", line)
        name = re.sub(r"^[0-9a-fA-F]* [ |*](.*)", r"\1", line)
        recorded[name] = digest
        order.append(name)
    present = {}
    for name in _files_under(directory):
        if name == "MD5":
            continue
        digest = md5sum(os.path.join(directory, name))
        present[name] = next(iter(digest.values()))
    result = True
    missing = [name for name in order if name not in present]
    if missing:
        result = False
        quoted = ", ".join(_quote(name) for name in missing)
        if len(missing) > 1:
            print(f"files {quoted} are missing", file=sys.stdout)
        else:
            print(f"file {_quote(missing[0])} is missing", file=sys.stdout)
    compared = [name for name in order if name not in missing]
    wrong = [name for name in compared if recorded[name] != present[name]]
    if wrong:
        result = False
        if len(wrong) > 1:
            print("files " + ", ".join(_quote(name) for name in wrong) + " have the wrong MD5 checksums")
        else:
            print(f"file {_quote(wrong[0])} has the wrong MD5 checksum")
    return result
