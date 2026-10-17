"""File assertions. has_extension calls tools.file_ext."""

from __future__ import annotations

import os
from typing import Any

from assertthat.expr import register
from assertthat.failure import on_failure
from assertthat.see import assert_that
from tools.file_ext import file_ext


def _bind(path: Any) -> dict[str, Any]:
    return {"path": path}


def is_dir(path: Any) -> bool:
    assert_that("is.string(path)", "file.exists(path)", env=_bind(path))
    return os.path.isdir(path)


def is_writeable(path: Any) -> bool:
    assert_that("is.string(path)", "file.exists(path)", env=_bind(path))
    return os.access(path, os.W_OK)


def is_readable(path: Any) -> bool:
    assert_that("is.string(path)", "file.exists(path)", env=_bind(path))
    return os.access(path, os.R_OK)


def has_extension(path: Any, ext: Any) -> bool:
    found = file_ext(path)
    if isinstance(found, list) or isinstance(ext, (list, tuple)):
        left = found if isinstance(found, list) else [found]
        right = list(ext) if isinstance(ext, (list, tuple)) else [ext]
        if len(right) == 1 and len(left) != 1:
            right = right * len(left)
        return all(item == other for item, other in zip(left, right)) and len(left) == len(right)
    return found == ext


def _path_is_not(thing: str):
    def fail(call: Any, env: dict[str, Any]) -> str:
        from assertthat.expr import evaluate

        path = evaluate(call["path"], env)
        return f"Path '{path}' is not {thing}"

    return fail


def _has_extension_fail(call: Any, env: dict[str, Any]) -> str:
    from assertthat.expr import evaluate

    path = evaluate(call["path"], env)
    ext = evaluate(call["ext"], env)
    return f"File '{os.path.basename(str(path))}' does not have extension {ext}"


def install_files() -> None:
    register("is.dir", is_dir, ["path"])
    register("is.writeable", is_writeable, ["path"])
    register("is.readable", is_readable, ["path"])
    register("has_extension", has_extension, ["path", "ext"])
    on_failure(is_dir, _path_is_not("a directory"))
    on_failure(is_writeable, _path_is_not("writeable"))
    on_failure(is_readable, _path_is_not("readable"))
    on_failure(has_extension, _has_extension_fail)


install_files()
