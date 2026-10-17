"""Path helpers from tools 4.5.0.

file_path_sans_ext uses the same [[:alnum:]] class as file_ext. list.files
sorting is the locale sort of the names. Extension patterns are not escaped,
so a dot inside an extension such as tab.gz matches any character.
"""

from __future__ import annotations

import os
import re
from typing import Any

from tools.file_ext import NA, NA_character_, _is_alnum

_COMPRESSION = (".gz", ".bz2", ".xz")
_CODE_EXT = ("R", "r", "S", "s", "q")
_DATA_EXT = (
    "R", "r", "RData", "rdata", "rda", "tab", "txt", "TXT",
    "tab.gz", "txt.gz", "tab.bz2", "txt.bz2", "tab.xz", "txt.xz",
    "csv", "CSV", "csv.gz", "csv.bz2", "csv.xz",
)
_DEMO_EXT = ("R", "r")
_DOCS_EXT = ("Rd", "rd")
_VIGNETTE_EXT = (
    "Rnw", "rnw", "Snw", "snw", "Rtex", "rtex", "Stex", "stex", "Rmd",
)


def _one_sans(text: str | NA, compression: bool) -> str | NA:
    if isinstance(text, NA):
        return NA_character_
    if compression:
        for suffix in _COMPRESSION:
            if text.endswith(suffix):
                text = text[: -len(suffix)]
                break
    end = len(text)
    start = end
    while start > 0 and _is_alnum(text[start - 1]):
        start -= 1
    if start == end or start == 0 or text[start - 1] != ".":
        return text
    # ([^.]+) must be a non-empty run of non-dots immediately before that dot.
    left = start - 1
    if left == 0 or text[left - 1] == ".":
        return text
    return text[:left]


def file_path_sans_ext(x: Any, compression: bool = False) -> Any:
    """Drop a trailing alphanumeric extension. compression also drops gz, bz2, or xz."""
    if x is None or x == []:
        return []
    if isinstance(x, (str, NA)):
        return _one_sans(x, compression)
    return [_one_sans(item if isinstance(item, (str, NA)) else NA_character_, compression) for item in x]


def file_path_as_absolute(x: Any) -> str:
    """Expand and normalize one existing path. The separator is /."""
    if isinstance(x, (list, tuple)):
        if len(x) != 1:
            raise ValueError("'x' must be a character string")
        x = x[0]
    if not isinstance(x, str):
        raise ValueError("'x' must be a character string")
    expanded = os.path.expanduser(x)
    if not os.path.exists(expanded):
        raise ValueError(f"file '{x}' does not exist")
    return os.path.realpath(expanded)


def _list_names(directory: str, all_files: bool) -> list[str]:
    names = os.listdir(directory)
    if not all_files:
        names = [name for name in names if not name.startswith(".")]
    return sorted(names)


def list_files_with_exts(directory: str, exts: Any, all_files: bool = False, full_names: bool = True) -> list[str]:
    """Names in directory whose extension matches one of exts."""
    if isinstance(exts, str):
        exts = [exts]
    pattern = re.compile(r"\.(" + "|".join(exts) + r")$")
    files = [name for name in _list_names(directory, all_files) if pattern.search(name)]
    if not full_names:
        return files
    if not files:
        return []
    return [os.path.join(directory, name) for name in files]


def _file_exts(type_name: str) -> tuple[str, ...]:
    choices = {
        "code": _CODE_EXT,
        "data": _DATA_EXT,
        "demo": _DEMO_EXT,
        "docs": _DOCS_EXT,
        "vignette": _VIGNETTE_EXT,
    }
    if type_name not in choices:
        raise ValueError(f"'type' should be one of {', '.join(repr(name) for name in choices)}")
    return choices[type_name]


def _os_type() -> str:
    if "R_OSTYPE" in os.environ and os.environ["R_OSTYPE"]:
        return os.environ["R_OSTYPE"]
    return "windows" if os.name == "nt" else "unix"


def list_files_with_type(
    directory: str,
    type_name: str,
    all_files: bool = False,
    full_names: bool = True,
    os_subdirs: Any = None,
) -> list[str]:
    """Files of one R type. code and docs also look in OS subdirectories."""
    exts = _file_exts(type_name)
    files = list_files_with_exts(directory, exts, all_files=all_files, full_names=full_names)
    if os_subdirs is None:
        os_subdirs = [_os_type()]
    elif isinstance(os_subdirs, str):
        os_subdirs = [os_subdirs]
    if type_name in ("code", "docs"):
        for name in os_subdirs:
            os_dir = os.path.join(directory, name)
            if os.path.isdir(os_dir):
                found = list_files_with_exts(os_dir, exts, all_files=all_files, full_names=False)
                prefix = os_dir if full_names else name
                files.extend(os.path.join(prefix, item) for item in found)
        files = [item for item in files if re.match(r"^[A-Za-z0-9]", os.path.basename(item))]
    if type_name == "demo":
        files = [item for item in files if re.match(r"^[A-Za-z]", os.path.basename(item))]
    return files
