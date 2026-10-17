"""Check R source and examples for bare T or F (tools::checkTnF)."""

from __future__ import annotations

import os
import subprocess
import warnings
from pathlib import Path
from typing import Any

from tools.paths import (
    file_path_as_absolute,
    list_files_with_exts,
    list_files_with_type,
)
from tools.rd_help import _find_package

_R_HELPER = Path(__file__).with_name("check_tnf_r.R")


class CheckTnF(dict[str, list[str]]):
    """Mapping from file path to deparsed expressions that use T or F."""


def _r_helper(*argv: str) -> subprocess.CompletedProcess[str]:
    command = ["Rscript", "--vanilla", str(_R_HELPER), *argv]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _find_tnf_in_code(file: str, text: str | None = None) -> list[str]:
    args = ["find", file, "" if text is None else text]
    completed = _r_helper(*args)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(message)
    output = completed.stdout
    if not output:
        return []
    return output.splitlines()


def _rd_example_code(path: str) -> str:
    completed = _r_helper("examples", path)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(message)
    return completed.stdout


def _find_package_dir(package: str, lib_loc: list[str] | None) -> Path:
    if lib_loc is None:
        return _find_package(package, None)
    last: ValueError | None = None
    for loc in lib_loc:
        try:
            return _find_package(package, Path(loc))
        except ValueError as exc:
            last = exc
    if last is not None:
        raise last
    return _find_package(package, None)


def format_check_tnf(x: CheckTnF) -> list[str]:
    """The same lines as format.checkTnF in tools."""
    lines: list[str] = []
    for fname in x:
        lines.append(f"File '{fname}':")
        for expr in x[fname]:
            text = f"found T/F in {expr}"
            if len(text) <= 76:
                wrapped = [text]
            else:
                wrapped = [text[:76]]
                index = 76
                while index < len(text):
                    wrapped.append("    " + text[index : index + 72])
                    index += 72
            lines.extend(wrapped)
        lines.append("")
    return lines


def check_tnf(
    package: str | None = None,
    dir: str | None = None,
    file: str | None = None,
    lib_loc: list[str] | None = None,
) -> CheckTnF:
    """Check a package, source tree, or file for uses of T or F instead of TRUE or FALSE."""
    code_files: list[str] = []
    docs_files: list[str] = []

    if package is not None:
        if isinstance(package, (list, tuple)) or not isinstance(package, str):
            raise ValueError("argument 'package' must be of length 1")
        directory = _find_package_dir(package, lib_loc)
        if (directory / "R" / "all.rda").is_file():
            warnings.warn("cannot check R code installed as image", stacklevel=2)
        code_file = directory / "R" / package
        if code_file.is_file():
            code_files = [str(code_file)]
        example_dir = directory / "R-ex"
        if example_dir.is_dir():
            code_files.extend(list_files_with_exts(str(example_dir), "R"))
    elif dir is not None:
        if not os.path.isdir(dir):
            raise ValueError(f"directory '{dir}' does not exist")
        dir = file_path_as_absolute(dir)
        code_dir = os.path.join(dir, "R")
        if os.path.isdir(code_dir):
            code_files = list_files_with_type(code_dir, "code")
        docs_dir = os.path.join(dir, "man")
        if os.path.isdir(docs_dir):
            docs_files = list_files_with_type(docs_dir, "docs")
    elif file is not None:
        if not os.path.isfile(file):
            raise ValueError(f"file '{file}' does not exist")
        code_files = [file]
    else:
        raise ValueError("you must specify 'package', 'dir' or 'file'")

    bad_exprs: CheckTnF = CheckTnF()
    for path in code_files:
        exprs = _find_tnf_in_code(path)
        if exprs:
            bad_exprs[path] = exprs

    for path in docs_files:
        text = _rd_example_code(path)
        exprs = _find_tnf_in_code(path, text)
        if exprs:
            bad_exprs[path] = exprs

    return bad_exprs
