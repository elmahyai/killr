"""Checks for the cli, pbcol, and tutorial progression handlers."""

import contextlib
import io

import pytest

import progressr.cli_handlers as cli_handlers
from cli import options as cli_options
from progressr.cli_handlers import handler_cli, handler_pbcol, handler_tutorial, pbcol
from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor

_STEPS = "{cli::pb_spin} {cli::pb_bar} {cli::pb_current}/{cli::pb_total} {cli::pb_status}"
_STEPS_DONE = "{cli::pb_bar} {cli::pb_current}/{cli::pb_total} {cli::pb_status}"
_PERCENT = "{cli::pb_spin} {cli::pb_bar} {cli::pb_percent} {cli::pb_status}"
_PERCENT_DONE = "{cli::pb_bar} {cli::pb_percent} {cli::pb_status}"
_TIME = (
    "[{cli::pb_elapsed}] {cli::pb_spin} {cli::pb_bar} {cli::pb_percent} "
    "[{cli::pb_current}/{cli::pb_total}] (ETA: {cli::pb_eta}) {cli::pb_status}"
)
_TIME_DONE = (
    "[{cli::pb_elapsed}] {cli::pb_bar} {cli::pb_percent} "
    "[{cli::pb_current}/{cli::pb_total}] {cli::pb_status}"
)


def _run(handler, steps, messages=True):
    buf = io.StringIO()

    def body():
        progress = progressor(steps=steps, on_exit=False)
        if messages and steps > 0:
            for index in range(1, steps + 1):
                progress(message=f"m{index}")

    with contextlib.redirect_stderr(buf):
        with_progress(
            body,
            handlers=handler,
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    return buf.getvalue()


def test_type_formats_and_match_arg():
    assert handler_cli(enable=True).backend_args == {}
    steps = handler_cli(type="steps", enable=True)
    assert steps.backend_args["format"] == _STEPS
    assert steps.backend_args["format_done"] == _STEPS_DONE
    percent = handler_cli(type="p", enable=True)
    assert percent.backend_args["format"] == _PERCENT
    assert percent.backend_args["format_done"] == _PERCENT_DONE
    timed = handler_cli(type="time", enable=True)
    assert timed.backend_args["format"] == _TIME
    assert timed.backend_args["format_done"] == _TIME_DONE
    custom = handler_cli(type="steps", format="CUSTOM", enable=True)
    assert custom.backend_args["format"] == "CUSTOM"
    assert custom.backend_args["format_done"] == _STEPS_DONE
    with pytest.raises(ProgressrError, match="should be one of"):
        handler_cli(type="nope")
    with pytest.raises(ProgressrError, match="Additional arguments must be named"):
        handler_cli(0.0, 1, "terminal", "steps", "extra")


def test_total_zero_skips_cli_and_clear_erases(monkeypatch):
    calls = []
    real = cli_handlers.cli_progress_bar

    def spy(*args, **kwargs):
        calls.append(kwargs.get("total", args[0] if args else None))
        return real(*args, **kwargs)

    monkeypatch.setattr(cli_handlers, "cli_progress_bar", spy)
    assert _run(handler_cli(clear=False, enable=True), 0, messages=False) == "\n"
    assert calls == []
    erased = _run(handler_cli(type="steps", clear=True, enable=True), 4)
    assert erased == "\r" + (" " * 79) + "\r"
    assert calls == [4.0] or calls == [4]


def test_steps_bar_is_only_an_id_and_a_newline(monkeypatch):
    calls = []
    real = cli_handlers.cli_progress_bar

    def spy(*args, **kwargs):
        calls.append(real(*args, **kwargs))
        return calls[-1]

    monkeypatch.setattr(cli_handlers, "cli_progress_bar", spy)
    text = _run(handler_cli(type="steps", clear=False, enable=True), 4)
    assert text == "\n"
    assert len(calls) == 1
    assert isinstance(calls[0], str) and calls[0].startswith("cli-")


def test_show_after_is_unused_and_enable_after_delays(monkeypatch):
    calls = []
    real = cli_handlers.cli_progress_bar

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(cli_handlers, "cli_progress_bar", spy)
    shown = _run(handler_cli(type="time", clear=False, show_after=1000, enable=True), 2)
    assert shown == "\n"
    assert calls == [1]
    calls.clear()
    quiet = _run(handler_cli(type="time", clear=False, enable=True, enable_after=1000), 2)
    assert quiet == ""
    assert calls == []


def test_pbcol_layout_and_default_colors():
    plain_colors = cli_options(**{"cli.num_colors": 1})
    try:
        assert pbcol(fraction=0.5, msg="Hi", width=20) == " Hi             50%  "
        assert pbcol(fraction=1, msg="", width=12) == "       100%  "
    finally:
        cli_options(**{"cli.num_colors": plain_colors.get("cli.num_colors")})
    previous = cli_options(**{"cli.num_colors": 8})
    try:
        colored = pbcol(fraction=0.5, msg="Hi", width=20)
    finally:
        cli_options(**{"cli.num_colors": previous.get("cli.num_colors")})
    assert "\x1b[44m" in colored
    assert "\x1b[37m" in colored
    assert "\x1b[46m" in colored
    plain = pbcol(fraction=0.5, msg="Hi", width=20, complete=None, incomplete=None)
    assert "\x1b[" not in plain


def test_pbcol_four_steps_keeps_the_last_line():
    handler = None
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        handler = handler_pbcol(clear=False, enable=True)

        def body():
            progress = progressor(steps=4, on_exit=False)
            for index in range(1, 5):
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
    text = buf.getvalue()
    assert text.endswith("\n")
    lines = text.split("\r")
    assert lines[0] == ""
    assert all(len(line) == 80 for line in lines[1:-1])
    assert lines[-1].endswith("\n")
    assert len(lines[-1]) == 81
    assert "100%" in lines[-1]
    assert handler._env["target"] == "terminal"
    cleared = _run(handler_pbcol(clear=True, enable=True), 4)
    assert cleared.endswith("\r")
    assert "100%" not in cleared.split("\r")[-1]


def test_tutorial_cli_spec():
    handler = handler_tutorial(spec="cli", enable=True)
    assert handler.classes[0] == "cli_progression_handler"
    assert handler._env["clear"] is False
    assert handler._env["target"] == "terminal"
    prefixed = handler_tutorial(spec="c", enable=True)
    assert prefixed.classes[0] == "cli_progression_handler"
    with pytest.raises(ProgressrError, match="should be one of"):
        handler_tutorial(spec="invalid")
    with pytest.raises(ProgressrError) as caught:
        handler_tutorial(spec="progress")
    assert "Please install package" not in str(caught.value)
