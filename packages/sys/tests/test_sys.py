"""Checks for process execution."""

import os
import signal
import time

import pytest

from r_sys import (
    as_text,
    eval_safe,
    exec_background,
    exec_internal,
    exec_status,
    exec_wait,
    windows_quote,
)


def test_windows_quote():
    assert windows_quote(["a", "", "a b", 'a"b', "a\\b"]) == [
        "a",
        '""',
        '"a b"',
        '"a\\"b"',
        "a\\b",
    ]
    assert windows_quote(None) is None


def test_as_text_lines():
    with pytest.warns(UserWarning, match="incomplete final line"):
        assert as_text(b"a\nb") == ["a", "b"]
    assert as_text(b"a\nb\n") == ["a", "b"]
    assert as_text(b"") == []


def test_exec_internal_printf():
    out = exec_internal("printf", ["%s", "hello"])
    assert out["status"] == 0
    assert out["stdout"] == b"hello"
    assert out["stderr"] == b""


def test_exec_wait_codes_and_missing():
    assert exec_wait("true", std_out=False, std_err=False) == 0
    assert exec_wait("false", std_out=False, std_err=False) == 1
    with pytest.raises(Exception, match="Failed to execute 'doesnotexist'"):
        exec_wait("doesnotexist", std_out=False, std_err=False)


def test_exec_status_word():
    pid = exec_background("sleep", ["30"], std_out=False, std_err=False)
    assert exec_status(pid, wait=False) is None
    os.kill(pid, signal.SIGTERM)
    time.sleep(0.2)
    assert exec_status(pid, wait=True) == 15
    pid = exec_background("false", std_out=False, std_err=False)
    time.sleep(0.2)
    assert exec_status(pid, wait=True) == 256


def test_timeout():
    with pytest.raises(Exception, match=r"timeout reached: 0.20sec"):
        exec_internal("sleep", ["2"], timeout=0.2)


def test_eval_safe_is_deprecated():
    with pytest.warns(UserWarning, match="eval_safe"):
        with pytest.raises(RuntimeError, match="unix"):
            eval_safe(1)
