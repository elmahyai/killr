"""Checks for freduce, functions, and the functional-sequence debuggers."""

from __future__ import annotations

import math

import pytest

from magrittr._fseq import FSeq
from magrittr.fseq import (
    _is_debugged,
    debug_fseq,
    debug_pipe,
    freduce,
    functions,
    undebug_fseq,
)


def _steps():
    def first(value):
        return value + 1

    def second(value):
        return value * 2

    def third(value):
        return value - 3

    return first, second, third


def test_freduce_applies_one_function():
    assert freduce(16, [math.sqrt]) == 4


def test_freduce_applies_each_function():
    calls = []

    def add_one(value):
        calls.append("add")
        return value + 1

    def times_two(value):
        calls.append("times")
        return value * 2

    assert freduce(3, [add_one, times_two]) == 8
    assert calls == ["add", "times"]


def test_freduce_empty_list_uses_the_r_message():
    with pytest.raises(
        IndexError,
        match="attempt to select less than one element in integerOneIndex",
    ):
        freduce(1, [])


def test_freduce_long_list_of_identities():
    def identity(value):
        return value

    assert freduce(1, [identity] * 1000) == 1


def test_functions_returns_the_stored_list():
    first, second, _third = _steps()
    fseq = FSeq([first, second])
    extracted = functions(fseq)
    assert extracted[0] is first
    assert extracted[1](extracted[0](16)) == 34
    assert len(extracted) == 2


def test_functions_rejects_a_plain_object():
    with pytest.raises(ValueError, match="Object is not a functional sequence."):
        functions(math.sqrt)


def test_debug_pipe_prints_the_browser_lines_and_returns_the_value(capsys):
    assert debug_pipe(5) == 5
    assert capsys.readouterr().out == "Called from: debug_pipe(5)\ndebug: x\n"


def test_debug_fseq_marks_the_selected_functions_and_returns_none():
    first, second, third = _steps()
    fseq = FSeq([first, second, third])
    assert debug_fseq(fseq, 2) is None
    assert _is_debugged(second)
    assert not _is_debugged(first)
    assert not _is_debugged(third)
    assert debug_fseq(fseq, 1, 3) is None
    assert _is_debugged(first)
    assert _is_debugged(third)


def test_debug_fseq_rejects_an_invalid_index():
    fseq = FSeq(_steps())
    for index in ((), (0,), (-1,), (4,), (1.5,), ("a",), (True,), (float("nan"),)):
        with pytest.raises(ValueError, match="Index or indices invalid."):
            debug_fseq(fseq, *index)


def test_debug_fseq_without_a_numeric_index_does_not_require_an_fseq():
    with pytest.raises(ValueError, match="Index or indices invalid."):
        debug_fseq("not a sequence")
    with pytest.raises(ValueError, match="Object is not a functional sequence."):
        debug_fseq("not a sequence", 1)


def test_debug_fseq_truncates_a_fraction_after_a_valid_index():
    first, second, third = _steps()
    fseq = FSeq([first, second, third])
    debug_fseq(fseq, 1, 2.2)
    assert _is_debugged(first)
    assert _is_debugged(second)
    assert not _is_debugged(third)
    undebug_fseq(fseq)
    with pytest.raises(IndexError, match="subscript out of bounds"):
        debug_fseq(fseq, 1, 99)
    assert _is_debugged(first)


def test_undebug_fseq_clears_marks_and_returns_none():
    first, second, third = _steps()
    fseq = FSeq([first, second, third])
    debug_fseq(fseq, 1, 3)
    assert undebug_fseq(fseq) is None
    assert not _is_debugged(first)
    assert not _is_debugged(second)
    assert not _is_debugged(third)
    assert undebug_fseq(fseq) is None
