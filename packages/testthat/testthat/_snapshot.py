"""Snapshots stored as text files. GitHub download is not implemented."""

from __future__ import annotations

import os

from testthat._core import fail, pass_, stop


def _dir() -> str:
    path = os.path.join(os.getcwd(), "_snaps")
    os.makedirs(path, exist_ok=True)
    return path


def announce(text: str, kind: str) -> str:
    path = os.path.join(_dir(), f"{kind}.txt")
    if not os.path.exists(path):
        open(path, "w", encoding="utf-8").write(text)
        pass_()
        return text
    old = open(path, encoding="utf-8").read()
    if old == text:
        pass_()
    else:
        fail(f"Snapshot of {kind} has changed.\nActual: {text}\nExpected: {old}")
    return text


def snapshot_value(code, style="json2", variant=None, transform=None):
    value = code() if callable(code) else code
    if transform is not None:
        value = transform(value)
    return announce(repr(value), variant or "value")


def snapshot_file(path, name, binary=None):
    data = open(path, "rb").read()
    dest = os.path.join(_dir(), os.path.basename(name) + (".bin" if binary else ".txt"))
    if not os.path.exists(dest):
        open(dest, "wb").write(data)
        pass_()
        return name
    if open(dest, "rb").read() == data:
        pass_()
    else:
        fail(f"Snapshot file {name} has changed.")
    return name


def _edition3(name: str) -> None:
    from testthat._core import edition_get
    if edition_get() < 3:
        stop(f"`{name}()` requires the 3rd edition.")


def announce_snapshot_file(path, name=None):
    _edition3("announce_snapshot_file")
    snapshot_file(path, name or path)
    return None


def snapshot_accept(files=None, path="tests/testthat"):
    print("No snapshots to update.")
    return None


def snapshot_reject(files=None, path="tests/testthat"):
    print("No snapshots to reject")
    return None


def snapshot_review(files=None, path=None):
    stop("The packages \"shiny\" and \"diffviewer\" are required to use\nsnapshot_review()")


def snapshot_download_gh(repository=None, run_id=None, dest_dir="."):
    if not repository:
        stop("`repository` must be a single string, not absent.")
    if not run_id:
        stop("`run_id` must be a single string, not absent.")
    stop("snapshot_download_gh() needs the gh package, which is not translated.")


def local_snapshotter():
    from contextlib import contextmanager
    from testthat._core import STATE

    @contextmanager
    def _ctx():
        old = STATE.snapshot
        STATE.snapshot = True
        try:
            yield
        finally:
            STATE.snapshot = old

    return _ctx()


def is_snapshot():
    from testthat._core import is_snapshot as _is
    return _is()
