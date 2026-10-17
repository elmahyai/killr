"""The text bar and the Tcl/Tk window match the captured R results."""

import contextlib
import io

import pytest

from progressr.backends import handler_progress, handler_tkprogressbar
from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor


_BAR = (
    "\r- [------------------------------]   0% "
    "\r\\ [======>---------------------]  25% m1"
    "\r| [=============>--------------]  50% m2"
    "\r/ [====================>-------]  75% m3"
    "\r- [============================] 100% m4\n"
)


def _bar():
    buf = io.StringIO()

    def body():
        progress = progressor(steps=4, on_exit=False)
        for index in range(1, 5):
            progress(message=f"m{index}")

    with contextlib.redirect_stderr(buf):
        with_progress(
            body,
            handlers=handler_progress(
                format=":spin [:bar] :percent :message",
                width=40,
                clear=False,
                enable=True,
            ),
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    return buf.getvalue()


def _open_bar(handler):
    finish = handler._env["reporter"]["initiate"]
    closed = dict(zip(finish.__code__.co_freevars, (cell.cell_contents for cell in finish.__closure__)))
    box = closed["pb_config"]
    if box[0] is None:
        return None
    return box[0]["pb"]


def _tk(steps, clear):
    handler = handler_tkprogressbar(clear=clear, enable=True)

    def body():
        progress = progressor(steps=4, on_exit=False)
        for index in range(1, steps + 1):
            progress(message=f"m{index}")

    with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    pb = _open_bar(handler)
    if pb is None:
        return {"gone": True}
    try:
        return pb.snapshot()
    finally:
        pb.kill()


def test_progress_bar_matches_the_r_line():
    assert _bar() == _BAR
    with pytest.raises(ProgressrError, match="should be one of"):
        handler_progress(type="nope")


def test_tk_window_matches_r_state():
    assert _tk(0, False) == {
        "gone": False,
        "title": "R progress bar",
        "label": "",
        "percent": 25.0,
        "geometry": "340x80",
    }
    assert _tk(1, False)["percent"] == 50.0
    assert _tk(1, False)["label"] == "m1"
    done = _tk(4, False)
    assert done["percent"] == 100.0
    assert done["label"] == "m4"
    assert done["geometry"] == "340x80"
    assert _tk(4, True) == {"gone": True}
    with pytest.raises(ProgressrError, match="is.list\\(inputs\\)"):
        handler_tkprogressbar(inputs="x", enable=True)
