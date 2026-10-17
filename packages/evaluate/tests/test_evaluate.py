"""Behavior checked against evaluate 1.0.5."""

import os

import pytest

from evaluate import (
    create_traceback,
    evaluate,
    flush_console,
    inject_funs,
    is_error,
    is_message,
    is_recordedplot,
    is_source,
    is_warning,
    local_reproducible_output,
    new_output_handler,
    parse_all,
    plot,
    remove_hooks,
    replay,
    set_hooks,
    trim_intermediate_plots,
    try_capture_stack,
)
from evaluate.core import message, stop, warning
from evaluate.parse import expr_label
from evaluate.state import STATE, option
from evaluate.types import Error, Message, Source, Warning


def test_parse_comments_and_semicolons():
    parsed = parse_all(["# a comment", "x", "x;y", "x;y;z"])
    assert parsed.src == ["# a comment\n", "x\n", "x;y\n", "x;y;z\n"]
    assert [expr_label(exprs) for exprs in parsed.expr] == [
        "expression()",
        "expression(x)",
        "expression(x, y)",
        "expression(x, y, z)",
    ]


def test_parse_multiline_function_keeps_comments_in_the_span():
    source = [
        "function() {}",
        "function() {",
        "  # Hello!",
        "}",
        "function() {",
        "  # Hello!",
        "  # Goodbye!",
        "}",
    ]
    parsed = parse_all(source)
    assert [len(exprs) for exprs in parsed.expr] == [1, 1, 1]
    assert parsed.src == [
        "function() {}\n",
        "function() {\n  # Hello!\n}\n",
        "function() {\n  # Hello!\n  # Goodbye!\n}\n",
    ]
    assert expr_label(parsed.expr[0]) == "expression(function() {\n})"


def test_parse_joins_a_continued_line_and_keeps_blank_lines():
    assert parse_all("1+\n2;3").src == ["1+\n2;3\n"]
    assert expr_label(parse_all("1+\n2;3").expr[0]) == "expression(1 + 2, 3)"
    assert parse_all("1\n+ 2").src == ["1\n", "+ 2\n"]
    assert [expr_label(exprs) for exprs in parse_all("1\n+ 2").expr] == [
        "expression(1)",
        "expression(+2)",
    ]
    assert parse_all("(1\n+ 2)").src == ["(1\n+ 2)\n"]
    assert expr_label(parse_all("(1\n+ 2)").expr[0]) == "expression((1 + 2))"
    assert parse_all("a\n\nb").src == ["a\n", "\n", "b\n"]
    assert parse_all("").src == ["\n"]
    assert parse_all("#").src == ["#\n"]
    assert parse_all("\n\n").src == ["\n", "\n"]
    assert parse_all(["\n", "", "1"]).src == ["\n", "\n", "1\n"]
    assert parse_all([]).src == []


def test_parse_error_matches_the_installed_message():
    with pytest.raises(Exception) as caught:
        parse_all("x <-")
    assert str(caught.value) == "<text>:2:0: unexpected end of input\n1: x <-\n   ^"
    failed = parse_all("x <-", allow_error=True)
    assert failed.error is not None
    assert failed.src == ["x <-"]


def test_evaluate_prints_visible_values():
    text = str(evaluate(["1 + 1", "2 + 2"], envir={}))
    assert text == (
        "<evaluation>\n"
        "Source code: \n"
        "  1 + 1\n"
        "Text output: \n"
        "  [1] 2\n"
        "Source code: \n"
        "  2 + 2\n"
        "Text output: \n"
        "  [1] 4"
    )


def test_semicolon_stops_the_rest_of_the_line():
    text = str(evaluate("1;stop(2);3", envir={}))
    assert "Error:" in text
    assert "\n  2" in text
    assert "Text output: \n  [1] 3" not in text
    continued = str(evaluate(["1", "stop(2)", "3"], envir={}))
    assert "Source code: \n  3" in continued
    assert "[1] 3" in continued


def test_stop_on_error_2_raises():
    with pytest.raises(Error) as caught:
        evaluate("1;stop(2);3", envir={}, stop_on_error=2)
    assert caught.value.message == "2"


def test_message_and_warning_are_conditions():
    ev = evaluate('warning("hi")', envir={})
    assert is_warning(ev[1])
    assert ev[1].call is None
    ev = evaluate('message("hi")', envir={})
    assert is_message(ev[1])
    assert str(ev).splitlines()[-1] == "  hi"
    ev = evaluate('message("hi")', envir={}, keep_message=False)
    assert len(ev) == 1
    ev = evaluate("abcdef", envir={})
    assert is_error(ev[1])
    assert ev[1].message == "object 'abcdef' not found"


def test_warn_option():
    STATE.options["warn"] = -1
    try:
        ev = evaluate('warning("hi")', envir={})
        assert len(ev) == 1
        STATE.options["warn"] = 2
        ev = evaluate('warning("hi")', envir={})
        assert is_error(ev[1])
        assert ev[1].message == "(converted from warning) hi"
    finally:
        STATE.options["warn"] = 0


def test_replay_prompts_and_conditions():
    source = (
        "f1 <- function() {\n"
        '  cat("1\\n")\n'
        '  print("2")\n'
        '  warning("3")\n'
        '  print("4")\n'
        '  message("5")\n'
        '  stop("6")\n'
        "}\n"
    )
    evaluate(source, envir={})
    # f1 is defined in a private env above. Define it in the env we replay.
    env = {}
    evaluate(source, envir=env)
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        replay(evaluate("f1()", envir=env))
    assert buf.getvalue() == (
        "> f1()\n"
        "1\n"
        '[1] "2"\n'
        "Warning in f1():\n"
        "3\n"
        '[1] "4"\n'
        "5\n"
        "Error in f1():\n"
        "6\n"
    )


def test_flush_splits_text():
    source = 'test <- function() { cat("hi"); flush_console(); cat("bye") }\n'
    env = {}
    evaluate(source, envir=env)
    ev = evaluate("test()", envir=env)
    assert ev[1] == "hi"
    assert ev[2] == "bye"


def test_inject_only_fills_missing_names():
    old = inject_funs(f=lambda: 1)
    try:
        ev = evaluate("f()", envir={})
        assert ev[1] == "[1] 1\n"
    finally:
        inject_funs(old)


def test_hooks_fire_until_removed():
    box = []
    new1 = {"before.plot.new": lambda: box.append("Plotted!")}
    set_hooks(new1)
    plot(1)
    remove_hooks(new1)
    plot(1)
    assert box == ["Plotted!"]
    STATE.devices.clear()


def test_reproducible_output_restores():
    before = option("width")
    previous = os.environ.get("NO_COLOR")
    with local_reproducible_output(width=40, color=False):
        assert option("width") == 40
        assert os.environ["NO_COLOR"] == "1"
        assert os.environ["LC_COLLATE"] == "C"
    assert option("width") == before
    assert os.environ.get("NO_COLOR") == previous


def test_traceback_and_stack():
    assert create_traceback([]) is None
    calls = create_traceback(["f()", "g(1, 2)"])
    assert calls == ["1: f()", "2: g(1, 2)"]
    caught = try_capture_stack('stop("boom")', {})
    assert caught.message == "boom"
    assert create_traceback(caught.calls) == ['1: stop("boom")']


def test_plots_trim_to_the_final_display_list():
    ev = evaluate(["plot(1:3)", 'text(1, 1, "x")', 'text(1, 1, "y")'], envir={})
    assert [type(item).__name__ for item in ev].count("RecordedPlot") == 3
    trimmed = trim_intermediate_plots(ev)
    plots = [item for item in trimmed if is_recordedplot(item)]
    assert len(plots) == 1
    assert len(plots[0].dl) == 10
    labels = []
    for call in plots[0].dl:
        if call.name == "C_text":
            labels.extend(call.data["labels"])
    assert labels == ["x", "y"]
    assert is_source(trimmed[0])


def test_mfrow_waits_for_the_page():
    source = "par(mfrow = c(1, 2))\nplot(1)\nplot(2)\n"
    ev = evaluate(source, envir={})
    kinds = []
    for item in ev:
        if is_source(item):
            kinds.append("source")
        elif is_recordedplot(item):
            kinds.append("plot")
    assert kinds == ["source", "source", "source", "plot"]


def test_output_handler_can_keep_the_value():
    handler = new_output_handler(value=lambda x: x)
    ev = evaluate("1 + 1", envir={}, output_handler=handler)
    assert ev[-1] == 2


def test_predicates():
    assert is_message(Message("hi\n"))
    assert not is_message(Warning("hi"))
    assert is_warning(Warning("hi"))
    assert is_error(Error("hi"))
    assert is_source(Source("x\n"))
    assert not is_recordedplot(Source("x\n"))


def test_bad_arguments():
    with pytest.raises(ValueError, match="stop_on_error"):
        evaluate("1", stop_on_error=4)
    with pytest.raises(ValueError, match="keep_message"):
        evaluate("1", keep_message=1)
    with pytest.raises(ValueError, match="calling_handlers"):
        new_output_handler(calling_handlers={"message": 1})
