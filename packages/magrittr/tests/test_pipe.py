"""Checks for the magrittr pipes."""

import contextlib
import io

import pytest

from magrittr._fseq import FSeq
from magrittr.pipe import (
    DOT,
    compound,
    eager,
    exposition,
    pipe,
    pipe_eager_lexical,
    pipe_lazy_masking,
    pipe_nested,
    tee,
)


def fsub(a, b):
    return a - b


def _say(word, give=None):
    def step(value):
        print(word)
        if give is None:
            return value
        return give

    return step


def _lines(call):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = call()
    return buffer.getvalue().splitlines(), result


def test_sum_of_one_to_ten_is_55():
    assert pipe(list(range(1, 11)), sum) == 55


def test_first_argument_and_dot_insertion():
    assert pipe(10, (fsub, (3,), {})) == 7
    assert pipe(10, (fsub, (3, DOT), {})) == -7
    assert pipe(10, (fsub, (), {"a": 3, "b": DOT})) == -7
    assert pipe(10, (fsub, (DOT, DOT), {})) == 0


def test_dot_starts_a_functional_sequence():
    sequence = pipe(DOT, sum)
    assert isinstance(sequence, FSeq)
    assert sequence._function_list == [sum]
    assert sequence(list(range(1, 11))) == 55

    dotted = pipe(DOT, (fsub, (3, DOT), {}))
    assert dotted._function_list[0] is not fsub
    assert dotted(10) == -7
    assert pipe(DOT)(5) == 5


def test_lazy_messages_run_from_the_last_step():
    foo, bar, baz = _say("foo"), _say("bar"), _say("baz")
    lines, result = _lines(lambda: pipe(None, foo, bar, baz))
    assert lines == ["baz", "bar", "foo"]
    assert result is None

    lines, result = _lines(lambda: pipe_lazy_masking(None, foo, bar, baz))
    assert lines == ["baz", "bar", "foo"]
    assert result is None


def test_unused_lazy_steps_do_not_run():
    lines, result = _lines(lambda: pipe(5, _say("foo", 1), _say("bar", 2), _say("baz", 3)))
    assert lines == ["baz"]
    assert result == 3


def test_eager_messages_run_forward_and_eager_is_the_lexical_pipe():
    assert eager is pipe_eager_lexical
    foo, bar, baz = _say("foo"), _say("bar"), _say("baz")
    lines, result = _lines(lambda: eager(None, foo, bar, baz))
    assert lines == ["foo", "bar", "baz"]
    assert result is None
    lines, result = _lines(
        lambda: pipe_eager_lexical(5, _say("foo", 1), _say("bar", 2), _say("baz", 3))
    )
    assert lines == ["foo", "bar", "baz"]
    assert result == 3
    assert eager(10, (fsub, (3, DOT), {})) == -7
    assert pipe_eager_lexical(list(range(1, 11)), sum) == 55


def test_nested_matches_pipe_for_pure_functions_and_rejects_two_dots():
    assert pipe_nested(list(range(1, 11)), sum) == 55
    assert pipe_nested(10, (fsub, (3, DOT), {})) == -7
    lines, result = _lines(lambda: pipe_nested(None, _say("foo"), _say("bar"), _say("baz")))
    assert lines == ["baz", "bar", "foo"]
    assert result is None
    lines, result = _lines(
        lambda: pipe_nested(5, _say("foo", 1), _say("bar", 2), _say("baz", 3))
    )
    assert lines == ["baz"]
    assert result == 3

    seen = []

    def boom(value):
        seen.append("boom")
        return value

    with pytest.raises(ValueError, match="multiple placeholders"):
        pipe_nested(1, boom, (fsub, (DOT, DOT), {}))
    assert seen == []
    assert pipe_nested(DOT, (fsub, (DOT, DOT), {}))(10) == 0


def test_compound_assigns_into_the_dict_and_can_just_pipe():
    assert compound(list(range(1, 11)), sum) == 55
    namespace = {"x": list(range(1, 11))}
    assert compound(namespace, "x", sum) == 55
    assert namespace["x"] == 55
    namespace = {"y": 10}
    assert compound(namespace, "y", (fsub, (3, DOT), {})) == -7
    assert namespace["y"] == -7
    lines, result = _lines(
        lambda: compound({"z": None}, "z", _say("foo"), _say("bar"), _say("baz"))
    )
    assert lines == ["baz", "bar", "foo"]
    assert result is None


def test_tee_returns_the_original_and_still_runs_every_step():
    data = list(range(1, 11))
    assert tee(data, sum) is data
    lines, result = _lines(lambda: tee(None, _say("foo"), _say("bar"), _say("baz")))
    assert lines == ["baz", "bar", "foo"]
    assert result is None
    lines, result = _lines(lambda: tee(5, _say("foo", 1), _say("bar", 2), _say("baz", 3)))
    assert lines == ["baz", "bar", "foo"]
    assert result == 5


def test_exposition_passes_matching_names():
    assert exposition({"z": [1, 2, 3]}, lambda z: sum(z)) == 6
    assert exposition({"z": [1, 2, 3], "a": 10}, lambda z: sum(z)) == 6
    assert exposition({"z": [1, 2, 3], "a": 4}, lambda z, a: sum(z) + a) == 10
