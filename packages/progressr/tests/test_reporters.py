"""Checks for the text, bell, file-size, and slowdown reporters."""

import contextlib
import io
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor
from progressr.reporters import (
    handler_ascii_alert,
    handler_debug,
    handler_filesize,
    handler_newline,
    handler_slowdown,
    handler_void,
)

_LINE = re.compile(
    r"^\[.*?\] \(([0-9.]+)s => \+[+-]?[0-9.]+s\) ([^:]+): ([0-9.]+)/([0-9.]+) "
    r"\(([+-][^)]*)\) '(.*)' \{clear=([^,]*), enabled=([^,]*), status=(.*)\}"
    r"(?: \[progressor=.*, owner=.*\])?$"
)


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


def _parse(text):
    events = []
    for line in text.splitlines():
        match = _LINE.match(line)
        assert match, line
        events.append(
            {
                "dt": float(match.group(1)),
                "type": match.group(2),
                "step": float(match.group(3)),
                "max_steps": float(match.group(4)),
                "delta": float(match.group(5)),
                "message": match.group(6),
                "clear": match.group(7),
                "enabled": match.group(8),
                "status": match.group(9),
                "uuid": " [progressor=" in line,
            }
        )
    return events


def _fresh(name):
    directory = tempfile.mkdtemp()
    return os.path.join(directory, name)


def test_void_is_silent_and_disabled_by_default():
    handler = handler_void()
    assert handler._env["enable"] is False
    assert handler._env["target"] == "void"
    assert handler._env["intrusiveness"] == 0
    assert handler._env["reporter"]["initiate"](None, None, None) is None
    assert handler._env["reporter"]["update"](None, None, None) is None
    assert handler._env["reporter"]["finish"](None, None, None) is None

    out = io.StringIO()
    err = io.StringIO()

    def body():
        progress = progressor(steps=2, on_exit=False)
        progress(message="a")
        progress(message="b")
        return 6

    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        assert _run(handler_void(enable=True), body) == 6
    assert out.getvalue() == ""
    assert err.getvalue() == ""


def test_newline_writes_symbol_and_frames_interrupt():
    path = _fresh("newline.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=3, on_exit=False)
        progress(message="a")
        progress(amount=0, message="still")
        progress(type="hide", class_="control_progression", amount=0)
        progress(type="unhide", class_="control_progression", amount=0)
        progress(message="halted", amount=0, type="interrupt", class_="control_progression")
        progress(message="b")
        progress(message="c")

    _run(handler_newline(file=handle, enable=True), body)
    handle.close()
    assert open(path, encoding="utf-8").read() == "\n\n\n\nhalted\n\n\n\n"
    bare = handler_newline()
    assert bare._env["target"] == "terminal"
    assert bare._env["intrusiveness"] == 0


def test_ascii_alert_skips_zero_amount_and_frames_interrupt():
    path = _fresh("alert.txt")
    handle = open(path, "w", encoding="utf-8", newline="\n")

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="a")
        progress(amount=0, message="zero")
        progress(message="ding", amount=0, type="interrupt", class_="control_progression")
        progress(message="b")
        progress(message="c")
        progress(message="d")

    _run(handler_ascii_alert(file=handle, enable=True, intrusiveness=1), body)
    handle.close()
    assert open(path, encoding="utf-8").read() == "\a\nding\n\a\a\a"
    bare = handler_ascii_alert()
    assert bare._env["intrusiveness"] == 5
    assert tuple(bare._env["target"]) == ("terminal", "audio")


def test_debug_fields_and_uuid_suffix():
    err = io.StringIO()

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(message="one")
        progress(message="two", amount=0, class_="sticky")
        progress(message="halt", amount=0, type="interrupt", class_="control_progression")
        progress(message="three")
        progress(message="four")

    with contextlib.redirect_stderr(err):
        _run(handler_debug(enable=True, uuid=False), body)
    events = _parse(err.getvalue())
    assert [(item["type"], item["step"], item["max_steps"], item["delta"], item["message"], item["clear"], item["enabled"], item["status"]) for item in events] == [
        ("initiate", 0, 4, 0, "", "TRUE", "TRUE", ""),
        ("update", 1, 4, 1, "one", "TRUE", "TRUE", ""),
        ("update", 1, 4, 0, "two", "TRUE", "TRUE", ""),
        ("interrupt", 1, 4, 0, "two", "TRUE", "TRUE", ""),
        ("update", 2, 4, 1, "three", "TRUE", "TRUE", ""),
        ("update", 3, 4, 1, "four", "TRUE", "TRUE", ""),
        ("shutdown", 4, 4, 1, "four", "TRUE", "TRUE", "ok"),
        ("shutdown", 4, 4, 0, "four", "TRUE", "TRUE", "ok"),
    ]
    assert all(item["uuid"] is False for item in events)

    err = io.StringIO()

    def uuid_body():
        progress = progressor(steps=1, on_exit=False)
        progress(message="z")

    with contextlib.redirect_stderr(err):
        _run(handler_debug(enable=True, uuid=True), uuid_body)
    uuid_events = _parse(err.getvalue())
    assert [item["type"] for item in uuid_events] == ["initiate", "update", "update"]
    assert all(item["uuid"] is True for item in uuid_events)
    assert uuid_events[2]["delta"] == 0
    assert uuid_events[2]["message"] == "z"


def test_debug_reset_clears_the_clock(monkeypatch):
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    ticks = {"n": 0}

    def clock():
        return start + timedelta(seconds=ticks["n"])

    monkeypatch.setattr("progressr.reporters._clock", clock)
    err = io.StringIO()

    def body():
        progress = progressor(steps=2, on_exit=False, auto_finish=False)
        ticks["n"] = 5
        progress(message="a")
        progress(type="reset", class_="control_progression", amount=0)
        ticks["n"] = 9
        again = progressor(steps=1, on_exit=False, auto_finish=False)
        again(message="b")

    with contextlib.redirect_stderr(err):
        _run(handler_debug(enable=True), body)
    events = _parse(err.getvalue())
    assert events[0]["dt"] == 0
    assert events[1]["dt"] == 5
    assert events[1]["type"] == "update"
    initiate = [item for item in events if item["type"] == "initiate"]
    assert [item["dt"] for item in initiate] == [0, 0]


def test_slowdown_rejects_a_bad_duration_and_scales_the_sleep(monkeypatch):
    with pytest.raises(ProgressrError, match=r"duration >= 0 is not TRUE"):
        handler_slowdown(duration=-1)
    with pytest.raises(ProgressrError, match=r"is.finite\(duration\) is not TRUE"):
        handler_slowdown(duration=float("inf"))
    with pytest.raises(ProgressrError, match=r"is.finite\(duration\) is not TRUE"):
        handler_slowdown(duration=float("nan"))
    with pytest.raises(ProgressrError, match=r"length\(duration\) == 1L is not TRUE"):
        handler_slowdown(duration=[1, 2])
    with pytest.raises(ProgressrError, match=r"length\(duration\) == 1L is not TRUE"):
        handler_slowdown(duration=None)
    with pytest.raises(ProgressrError, match=r"is.numeric\(duration\) is not TRUE"):
        handler_slowdown(duration="a")
    with pytest.raises(ProgressrError, match=r"is.numeric\(duration\) is not TRUE"):
        handler_slowdown(duration=True)

    slept = []
    monkeypatch.setattr("progressr.reporters.time.sleep", lambda seconds: slept.append(seconds))

    def body():
        progress = progressor(steps=4, on_exit=False)
        progress(amount=1)
        progress(amount=1)
        progress(amount=2)
        return 1

    assert _run(handler_slowdown(duration=10, enable=True), body) == 1
    assert slept == [2.5, 2.5, 5.0]

    slept.clear()

    def quiet():
        progress = progressor(steps=2, on_exit=False)
        progress()
        progress()

    _run(handler_slowdown(duration=10, enable=True, enable_after=1e9), quiet)
    assert slept == []

    slept.clear()

    def zero():
        progress = progressor(steps=2, on_exit=False)
        progress()
        progress()
        return 3

    assert _run(handler_slowdown(duration=0, enable=True), zero) == 3
    assert slept == [0.0, 0.0]


def test_filesize_body_clear_and_truncation():
    path = _fresh("run.progress")
    box = {}

    def body():
        progress = progressor(steps=4, on_exit=False)
        box["init"] = os.path.getsize(path)
        progress(message="work")
        box["first"] = open(path, encoding="utf-8").read()
        progress(amount=0, message="hold")
        box["zero"] = open(path, encoding="utf-8").read()
        progress(message="broke", amount=1, type="interrupt", class_="control_progression")
        box["interrupt"] = open(path, encoding="utf-8").read()
        progress(message="go")
        progress(message="go")
        progress(message="go")

    _run(handler_filesize(file=path, enable=True, clear=False, intrusiveness=0), body)
    assert box["init"] == 0
    assert box["first"] == "1/4: work ......... [25%]"
    assert box["zero"] == box["first"]
    assert box["interrupt"] == "1/4: broke ........ [25%]"
    final = open(path, encoding="utf-8").read()
    assert final == "4/4: go ..................................................................................... [100%]"
    assert os.path.getsize(path) == 100

    cleared = _fresh("clear.progress")

    def clear_body():
        progress = progressor(steps=2, on_exit=False)
        progress(message="x")
        progress(message="y")

    _run(handler_filesize(file=cleared, enable=True, clear=True, intrusiveness=0), clear_body)
    assert os.path.exists(cleared) is False

    zero = _fresh("zero.progress")

    def zero_body():
        progressor(steps=0, on_exit=False)

    _run(handler_filesize(file=zero, enable=True, clear=False, intrusiveness=0), zero_body)
    assert open(zero, encoding="utf-8").read() == "0/0:  ....................................................................................... [100%]"
    assert os.path.getsize(zero) == 100

    missing = _fresh("off.progress")

    def off_body():
        progress = progressor(steps=2, on_exit=False)
        progress(message="x")
        progress(message="y")

    _run(handler_filesize(file=missing, enable=False), off_body)
    assert os.path.exists(missing) is False

    short = _fresh("short.progress")
    seen = {}

    def short_body():
        progress = progressor(steps=100, on_exit=False, auto_finish=False)
        progress(message="HELLO")
        seen["text"] = open(short, encoding="utf-8").read()
        seen["size"] = os.path.getsize(short)

    _run(handler_filesize(file=short, enable=True, clear=False, intrusiveness=0), short_body)
    assert seen["size"] == 1
    assert seen["text"] == "1"

    bare = handler_filesize(file=_fresh("default.progress"))
    assert bare._env["intrusiveness"] == 5
    assert bare._env["target"] == "file"
