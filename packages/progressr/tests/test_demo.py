"""Checks for the progressr demos and progress_aggregator."""

import io
import math
import warnings
from contextlib import redirect_stdout

import pytest

from progressr.aggregator import progress_aggregator
from progressr.condition import condition_message, inherits, progression, try_invoke_restart, with_calling_handlers
from progressr.demo import slow_sqrt, slow_sqrt_p, slow_sum, slow_sum_p
from progressr.evaluate import with_progress
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, set_option
from progressr.progressor import progressor


def _recording(**reporter):
    return make_progression_handler(
        "rec",
        reporter=reporter,
        enable=True,
        target="file",
        interval=0,
    )


def _run(body, handler):
    return with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )


def test_slow_sum_keeps_integer_storage():
    value = slow_sum(list(range(1, 11)), delay=0)
    assert type(value) is int
    assert value == 55
    floated = slow_sum([1.5, 2.5], delay=0)
    assert type(floated) is float
    assert floated == 4.0


def test_slow_sum_p_messages():
    lines = []

    def update(config, state, progression, **_kwargs):
        text = condition_message(progression).replace("\n", "")
        if text:
            lines.append(text)

    def on_message(condition):
        lines.append(condition_message(condition).replace("\n", ""))
        try_invoke_restart("muffleMessage", condition)

    def body():
        return slow_sum_p(
            list(range(1, 4)),
            delay=0,
            stdout=False,
            message=True,
            sticky=False,
            progress=True,
        )

    value = with_calling_handlers(
        lambda: _run(body, _recording(update=update)),
        message=on_message,
    )
    assert type(value) is int
    assert value == 6
    assert lines == [
        "P: Adding 1",
        "M: Added value 1",
        "P: Adding 2",
        "M: Added value 2",
        "P: Adding 3",
        "M: Added value 3",
    ]


def test_slow_sqrt_values():
    assert slow_sqrt([1, 4, 9], delay=0) == [1.0, 2.0, 3.0]
    assert slow_sqrt_p(
        [4, 9],
        delay=0,
        message=False,
        stdout=False,
        sticky=False,
        progress=False,
    ) == [2.0, 3.0]


def test_negative_sqrt_warns_once_per_call():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = slow_sqrt([-4], delay=0)
    assert len(caught) == 1
    assert str(caught[0].message) == "NaNs produced"
    assert math.isnan(result[0])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pair = slow_sqrt([-1, 4], delay=0)
    assert [str(item.message) for item in caught] == ["NaNs produced"]
    assert math.isnan(pair[0])
    assert pair[1] == 2.0


def test_stdout_and_hidden_option():
    set_option("progressr.slow_sum_p.stdout", True)
    try:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            slow_sum_p([1], delay=0, message=False, sticky=False, progress=False)
        assert buffer.getvalue() == "O: Element #1\n"

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            slow_sum_p([1], delay=0, stdout=False, message=False, sticky=False, progress=False)
        assert buffer.getvalue() == ""

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            slow_sum([1, 2], delay=0)
        assert buffer.getvalue() == ""
    finally:
        set_option("progressr.slow_sum_p.stdout", None)


def test_five_pauses_per_element(monkeypatch):
    calls = []
    monkeypatch.setattr("progressr.demo.time.sleep", lambda seconds: calls.append(seconds))
    slow_sum([1, 2], delay=0)
    assert calls == [0.0] * 10
    calls.clear()
    set_option("progressr.demo.delay", None)
    slow_sum([1], message=False)
    assert calls == [0.2] * 5
    calls.clear()
    slow_sqrt([4], message=False)
    assert calls == [0.1] * 5


def test_sticky_class_every_ten_elements():
    seen = []

    def grab(condition):
        text = condition_message(condition)
        if text == "P: 10 elements done":
            seen.append(condition.classes[0])

    def body():
        return slow_sum_p(
            list(range(1, 11)),
            delay=0,
            stdout=False,
            message=False,
            sticky=True,
            progress=True,
        )

    value = with_calling_handlers(
        lambda: _run(body, _recording()),
        progression=grab,
    )
    assert value == 55
    assert seen == ["sticky"]


def test_progress_aggregator_forwards_child_amounts():
    set_option("progressr.enable", True)
    amounts = []

    def update(config, state, progression, **_kwargs):
        child = progression.get("child")
        if child is not None:
            amounts.append(child["amount"])

    def body():
        progress = progressor(steps=2, initiate=True)
        relay = progress_aggregator(progress)
        assert relay.max_steps == 2
        assert relay.classes[0] == "progress_aggregator"

        def child():
            step = progressor(steps=2)
            step(amount=1)
            step(amount=1)
            return 2

        return relay(child)

    assert _run(body, _recording(update=update)) == 2
    assert amounts == [1.0, 1.0]


def test_aggregator_rejects_a_non_progressor_and_unknown_types():
    with pytest.raises(ProgressrError):
        progress_aggregator(lambda: None)

    set_option("progressr.enable", True)

    def body():
        progress = progressor(steps=2, initiate=True)
        return progress_aggregator(progress)

    relay = _run(body, _recording())
    handler = None
    for cell in relay.__closure__ or ():
        value = cell.cell_contents
        if callable(value) and inherits(value, "progression_handler"):
            handler = value
    assert handler is not None
    with pytest.raises(ProgressrError, match="Unknown 'progression' type"):
        handler(progression(type="nope", amount=1, progressor_uuid="u", progression_index=1))
    with pytest.raises(ProgressrError, match="control_progression"):
        handler(progression(type="hide", amount=1, progressor_uuid="u", progression_index=1))
