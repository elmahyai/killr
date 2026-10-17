"""Compare the translation with the installed filelock 1.0.3."""

from __future__ import annotations

import gc
import os
import subprocess
import tempfile
import textwrap
import time
import warnings
from pathlib import Path

import pytest

from filelock import FilelockError, lock, unlock

ROOT = Path(__file__).resolve().parents[1]


def _r(code: str) -> str:
    result = subprocess.run(["Rscript", "-e", code], text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout


def test_print_and_path_match_r():
    folder = Path(tempfile.mkdtemp(prefix="filelock-"))
    link = folder / "link"
    link.symlink_to(folder / "sub", target_is_directory=True)
    (folder / "sub").mkdir()
    relative = "rel.lock"
    cases = {
        "relative": relative,
        "dotdot": str(folder / "sub" / ".." / "b.lock"),
        "symlink": str(link / "a.lock"),
        "trail": str(folder / "trail.lock") + "/",
        "tilde": "~/filelock-home-probe.lock",
    }
    previous = os.getcwd()
    os.chdir(folder)
    try:
        for name, path in cases.items():
            held = lock(path)
            text = str(held)
            unlock(held)
            quoted = path.replace("\\", "\\\\").replace('"', '\\"')
            expected = _r(
                "suppressPackageStartupMessages(library(filelock)); "
                f'setwd("{folder}"); '
                f'l <- lock("{quoted}"); '
                "cat(paste(capture.output(print(l)), collapse = \"\\n\")); "
                "invisible(unlock(l))"
            )
            assert text == expected, name
    finally:
        os.chdir(previous)
        leftover = Path.home() / "filelock-home-probe.lock"
        if leftover.exists():
            leftover.unlink()


def test_errors_match_r():
    samples = [
        "lock(1)",
        'lock(c("a", "b"))',
        'lock("a", exclusive = "yes")',
        'lock("a", timeout = -1)',
        'unlock("a")',
        'lock("/tmp/no-such-filelock-dir/x")',
        'lock("/tmp/filelock-not-a-dir/x")',
    ]
    Path("/tmp/filelock-not-a-dir").write_text("x")
    mapping = {
        "lock(1)": lambda: lock(1),
        'lock(c("a", "b"))': lambda: lock(["a", "b"]),
        'lock("a", exclusive = "yes")': lambda: lock("a", exclusive="yes"),
        'lock("a", timeout = -1)': lambda: lock("a", timeout=-1),
        'unlock("a")': lambda: unlock("a"),
        'lock("/tmp/no-such-filelock-dir/x")': lambda: lock("/tmp/no-such-filelock-dir/x"),
        'lock("/tmp/filelock-not-a-dir/x")': lambda: lock("/tmp/filelock-not-a-dir/x"),
    }
    for sample in samples:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                mapping[sample]()
            except FilelockError as error:
                message = str(error)
            else:
                message = ""
        py_warn = [str(item.message) for item in caught]
        payload = _r(
            "suppressPackageStartupMessages(library(filelock)); "
            "options(warn = 1); "
            "ws <- character(); "
            f"withCallingHandlers(tryCatch({sample}, error = function(e) cat('ERR:', conditionMessage(e))), "
            "warning = function(w) { ws <<- c(ws, conditionMessage(w)); invokeRestart('muffleWarning') }); "
            "cat('\\nWARN:', paste(ws, collapse = ' | '))"
        )
        err, _, warn = payload.partition("\nWARN:")
        assert message == err.removeprefix("ERR:").strip(), sample
        if "No such file or directory" in warn:
            assert any("No such file or directory" in item for item in py_warn)


def test_exclusive_lock_blocks_r_and_a_second_handle_keeps_it():
    path = tempfile.mktemp(prefix="filelock-hold-")
    first = lock(path)
    second = lock(path)
    assert first == second
    blocked = _r(
        "suppressPackageStartupMessages(library(filelock)); "
        f'cat(if (is.null(lock("{path}", timeout = 0))) "NULL" else "LOCKED")'
    )
    assert blocked == "NULL"
    assert unlock(first) is True
    still = _r(
        "suppressPackageStartupMessages(library(filelock)); "
        f'cat(if (is.null(lock("{path}", timeout = 0))) "NULL" else "LOCKED")'
    )
    assert still == "NULL"
    assert "Unlocked" in str(first)
    assert "Unlocked" not in str(second)
    assert unlock(second) is True
    assert unlock(second) is True
    acquired = _r(
        "suppressPackageStartupMessages(library(filelock)); "
        f'l <- lock("{path}", timeout = 0); cat(if (is.null(l)) "NULL" else "LOCKED"); if (!is.null(l)) invisible(unlock(l))'
    )
    assert acquired == "LOCKED"
    assert "Unlocked" in str(second)


def test_shared_lock_is_visible_to_r():
    path = tempfile.mktemp(prefix="filelock-share-")
    held = lock(path, exclusive=False)
    script = textwrap.dedent(
        f"""
        suppressPackageStartupMessages(library(filelock))
            shared <- lock("{path}", exclusive = FALSE, timeout = 0)
            cat(if (is.null(shared)) "NULL" else "SHARED")
            if (!is.null(shared)) invisible(unlock(shared))
            cat(" ")
            exclusive <- lock("{path}", exclusive = TRUE, timeout = 0)
            cat(if (is.null(exclusive)) "NULL" else "EXCLUSIVE")
            if (!is.null(exclusive)) invisible(unlock(exclusive))
            invisible(NULL)
        """
    )
    result = subprocess.run(["Rscript", "-e", script], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "SHARED NULL"
    unlock(held)


def test_incompatible_types_match_r():
    path = tempfile.mktemp(prefix="filelock-mix-")
    held = lock(path, exclusive=True)
    with pytest.raises(FilelockError, match="File already has an exclusive lock"):
        lock(path, exclusive=False)
    unlock(held)
    held = lock(path, exclusive=False)
    with pytest.raises(FilelockError, match="File already has a shared lock"):
        lock(path, exclusive=True)
    unlock(held)


def test_finalizer_releases_the_lock_for_r():
    path = tempfile.mktemp(prefix="filelock-final-")
    held = lock(path)
    del held
    gc.collect()
    acquired = _r(
        "suppressPackageStartupMessages(library(filelock)); "
        f'l <- lock("{path}", timeout = 0); cat(if (is.null(l)) "NULL" else "LOCKED"); if (!is.null(l)) invisible(unlock(l))'
    )
    assert acquired == "LOCKED"


def test_timeout_is_empty_while_r_holds_the_lock():
    path = tempfile.mktemp(prefix="filelock-wait-")
    process = subprocess.Popen(
        [
            "Rscript",
            "-e",
            "suppressPackageStartupMessages(library(filelock)); "
            f'lock("{path}"); Sys.sleep(30)',
        ]
    )
    try:
        held = None
        for _ in range(100):
            probe = lock(path, timeout=0)
            if probe is None:
                held = True
                break
            unlock(probe)
            time.sleep(0.05)
        assert held
        started = time.perf_counter()
        assert lock(path, timeout=300) is None
        assert time.perf_counter() - started >= 0.25
    finally:
        process.kill()
        process.wait()


def test_created_file_mode_is_0600():
    path = tempfile.mktemp(prefix="filelock-mode-")
    held = lock(path)
    assert os.stat(path).st_mode & 0o777 == 0o600
    unlock(held)
