"""Checks for the text and Windows progress-bar handlers."""

import json
import os
import subprocess
import sys
import tempfile

import pytest

from progressr.bars import drop_ansi, handler_txtprogressbar, handler_winprogressbar
from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PY = os.environ.get("PROGRESSR_PYTHON", sys.executable)
_OS_ERROR = "handler_winprogressbar requires MS Windows: \u2018unix\u2019"


def _fresh(name):
    return os.path.join(tempfile.mkdtemp(), name)


def _run(handler, fn):
    return with_progress(
        fn,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )


def _proof(name, kind):
    suffix = "r.R" if kind == "r" else "py.py"
    path = os.path.join(_ROOT, "proof", f"{name}-{suffix}")
    if kind == "r":
        command = ["Rscript", path]
    else:
        command = [_PY, path]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_txtprogressbar_file_matches_r():
    r_out = _proof("handler_txtprogressbar", "r")
    py_out = _proof("handler_txtprogressbar", "py")
    assert py_out["style3"] == r_out["style3"]
    assert py_out["style1"] == r_out["style1"]
    assert "one" not in py_out["style3"]
    assert py_out["style1"].endswith("\n")
    assert "\r" not in py_out["style1"]


def test_winprogressbar_unix_error_matches_r():
    r_out = _proof("handler_winprogressbar", "r")
    py_out = _proof("handler_winprogressbar", "py")
    assert py_out["error"] == r_out["error"] == _OS_ERROR


def test_invalid_inputs_still_stop_on_the_os():
    with pytest.raises(ProgressrError, match="requires MS Windows") as caught:
        handler_winprogressbar(enable=True, inputs={"title": "nope"})
    assert str(caught.value) == _OS_ERROR


def test_unnamed_argument_is_rejected_before_the_os_check():
    with pytest.raises(ProgressrError) as caught:
        handler_winprogressbar(1, "gui", {"title": None}, "x")
    assert str(caught.value) == "Additional arguments must be named"


def test_disabled_text_handler_writes_nothing():
    path = _fresh("off.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="one")
        progress(message="two")
        progress(message="three")
        progress(message="four")

    _run(handler_txtprogressbar(file=handle, enable=False, clear=False), body)
    handle.close()
    assert open(path, "rb").read() == b""


def test_text_handler_defaults():
    handler = handler_txtprogressbar(enable=True)
    assert handler._env["intrusiveness"] == 1
    assert handler._env["target"] == "terminal"
    assert handler._env["clear"] is True
    path = _fresh("default.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="one")
        progress(message="two")
        progress(message="three")
        progress(message="four")

    _run(handler_txtprogressbar(file=handle, enable=True, clear=False), body)
    handle.close()
    text = open(path, "rb").read().decode("utf-8")
    assert "100%" in text
    assert text.endswith("\n")


def test_ansi_char_is_kept_and_width_uses_the_stripped_symbol():
    colored = "\x1b[31m=\x1b[39m"
    assert drop_ansi(colored) == "="
    with pytest.raises(Exception, match="non-zero width"):
        from progressr.bars import txtProgressBar2

        txtProgressBar2(min=0, max=2, char="\x1b[31m")
    path = _fresh("ansi.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="one")
        progress(message="two")
        progress(message="three")
        progress(message="four")

    _run(
        handler_txtprogressbar(char=colored, style=3, file=handle, enable=True, clear=False),
        body,
    )
    handle.close()
    text = open(path, "rb").read().decode("utf-8")
    assert "\x1b[31m" in text
    assert text.endswith("100%\n")
