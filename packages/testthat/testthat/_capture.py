"""Capture stdout and message() text."""

from __future__ import annotations

import contextlib
import io
from contextlib import contextmanager


_MESSAGES: list[list[str]] = []


def message(text: str) -> None:
    line = str(text)
    if not line.endswith("\n"):
        line += "\n"
    if _MESSAGES:
        _MESSAGES[-1].append(line)
    else:
        import sys
        sys.stderr.write(line)


@contextmanager
def take_messages(bucket: list[str]):
    _MESSAGES.append(bucket)
    try:
        yield bucket
    finally:
        _MESSAGES.pop()


def capture_output(code, print: bool = False, width: int = 80) -> str:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        value = code() if callable(code) else code
        if print and value is not None:
            print_value(value)
    return stream.getvalue()


def capture_output_lines(code, print: bool = False, width: int = 80) -> list[str]:
    text = capture_output(code, print=print, width=width)
    if text == "":
        return []
    return text.splitlines()


def print_value(value) -> None:
    print(value)


def capture_error(code):
    try:
        code() if callable(code) else code
    except Exception as exc:
        return exc
    return None


def capture_warning(code):
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        code() if callable(code) else code
    return caught[0] if caught else None


def capture_warnings(code):
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        code() if callable(code) else code
    return [str(item.message) for item in caught]


def capture_message(code):
    notes: list[str] = []
    with take_messages(notes):
        code() if callable(code) else code
    return notes[0] if notes else None


def capture_messages(code):
    notes: list[str] = []
    with take_messages(notes):
        code() if callable(code) else code
    return notes


def capture_condition(code):
    error = capture_error(code)
    if error is not None:
        return error
    warning = capture_warning(code)
    return warning


def capture_expectation(code):
    from testthat._core import Expectation
    try:
        code() if callable(code) else code
    except Expectation as exp:
        return exp
    return None


def evaluate_promise(code, print: bool = False, width: int = 80):
    notes: list[str] = []
    with take_messages(notes):
        output = capture_output(code, print=print, width=width)
        value = code() if callable(code) else code
    return {"result": value, "output": output, "messages": notes, "warnings": []}
