"""Checks for the progressr core: conditions, progressors, handlers, and with_progress."""

import warnings

import pytest

from progressr.condition import (
    condition_message,
    progression,
    signal_condition,
    with_calling_handlers,
)
from progressr.evaluate import with_progress, without_progress
from progressr.factory import make_progression_handler
from progressr.handlers import handlers
from progressr.options import ProgressrError, set_option, stop_if_not
from progressr.progressor import progressor


def _recording(**reporter):
    return make_progression_handler(
        "rec",
        reporter=reporter,
        enable=True,
        target="file",
        interval=0,
    )


def test_progression_fields_and_classes():
    condition = progression(message="hello", amount=2, type="update")
    assert condition["amount"] == 2.0
    assert condition["type"] == "update"
    assert condition_message(condition) == "hello"
    assert condition.classes == ("progression", "immediateCondition", "condition")
    assert "progression_time" in condition
    assert isinstance(condition["progression_time"], str)
    assert condition["session_uuid"]


def test_condition_message_pastes_and_calls():
    pasted = progression(message=["A", "B"], amount=1)
    assert condition_message(pasted) == "AB"
    dynamic = progression(message=lambda item: ["A", item["type"]], amount=1)
    assert condition_message(dynamic) == "Aupdate"
    empty = progression()
    assert condition_message(empty) == ""


def test_stop_if_not_uses_r_quotes():
    FALSE = False
    with pytest.raises(ProgressrError, match="\u2018FALSE\u2019 is not TRUE"):
        stop_if_not(FALSE)


def test_extra_names_must_be_nonempty():
    with pytest.raises(ProgressrError, match="is not TRUE"):
        progression(amount=1, **{"": 1})


def test_progressor_updates_and_length():
    seen = []

    def update(config, state, progression, **_kwargs):
        seen.append((progression["type"], progression["amount"], state["message"]))

    handler = _recording(update=update)

    def body():
        progress = progressor(steps=4)
        length = len(progress)
        for text in ("one", "two", "three", "four"):
            progress(message=text)
        return length

    assert with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    ) == 4
    assert seen == [
        ("update", 1.0, "one"),
        ("update", 1.0, "two"),
        ("update", 1.0, "three"),
        ("update", 1.0, "four"),
    ]


def test_progressor_rules():
    module = {"progressor": progressor}
    with pytest.raises(ProgressrError, match="global environment"):
        exec("progressor(steps=1, enable=True)", module, module)
    with pytest.raises(ProgressrError, match="on_exit = TRUE"):
        exec("from progressr.evaluate import with_progress\n", module, module)
        module["progressr_in_globalenv"] = __import__(
            "progressr.progressor", fromlist=["progressr_in_globalenv"]
        ).progressr_in_globalenv
        module["progressr_in_globalenv"]("allow")
        try:
            exec("progressor(steps=1, enable=True, on_exit=True)", module, module)
        finally:
            module["progressr_in_globalenv"]("disallow")

    def lengths():
        omitted = progressor(enable=True, initiate=False)
        transformed = progressor(steps=4, scale=2, offset=1, enable=True, initiate=False)
        explicit = progressor(steps=3, along=range(10), enable=True, initiate=False)
        return len(omitted), len(transformed), len(explicit)

    assert lengths() == (0, 9, 3)
    assert progressor(enable=False) is progressor(steps=3, enable=False)
    assert progressor(enable=False).enable is False


def test_step_amount_zero_and_owner():
    seen = []
    handler = _recording(
        update=lambda config, state, progression, **_kwargs: seen.append(
            (state["step"], progression.get("step"), progression["amount"])
        )
    )

    def go():
        signal_condition(progression(type="initiate", steps=10, auto_finish=False, progressor_uuid="s", progression_index=1))
        signal_condition(progression(type="update", step=3, message="s", progressor_uuid="s", progression_index=2))
        signal_condition(progression(type="update", step=3, message="t", progressor_uuid="s", progression_index=3))
        signal_condition(progression(type="update", amount=1, message="u", progressor_uuid="s", progression_index=4))
        signal_condition(progression(type="update", amount=1, progressor_uuid="other", progression_index=5))

    with_calling_handlers(go, progression=handler)
    assert seen == [(3.0, 3.0, 3.0), (3.0, 3.0, 0.0), (4.0, None, 1.0)]


def test_duplicate_progression_is_ignored():
    seen = []
    handler = _recording(
        initiate=lambda **_kwargs: seen.append("init"),
        update=lambda **_kwargs: seen.append("upd"),
    )
    from datetime import datetime

    stamp = datetime.now().astimezone()
    first = progression(
        type="initiate",
        steps=2,
        auto_finish=False,
        progressor_uuid="d",
        progression_index=1,
        progression_time=stamp,
        time=stamp,
    )
    second = progression(
        type="update",
        amount=1,
        message="a",
        progressor_uuid="d",
        progression_index=2,
        progression_time=stamp,
        time=stamp,
    )

    def go():
        signal_condition(first)
        signal_condition(first)
        signal_condition(second)
        signal_condition(second)

    with_calling_handlers(go, progression=handler)
    assert seen == ["init", "upd"]


def test_intrusiveness_scales_milestones_not_config():
    seen = []
    handler = make_progression_handler(
        "rec",
        reporter={
            "initiate": lambda config, state, progression, **_kwargs: seen.append(
                ("cfg", config["times"], config["interval"])
            ),
            "update": lambda config, state, progression, **_kwargs: seen.append(("step", state["step"])),
        },
        enable=True,
        times=4,
        interval=0,
        intrusiveness=2,
        target="file",
    )

    def go():
        signal_condition(progression(type="initiate", steps=8, auto_finish=False, progressor_uuid="i", progression_index=1))
        for index in range(1, 9):
            signal_condition(
                progression(type="update", amount=1, message="m", progressor_uuid="i", progression_index=index + 1)
            )

    with_calling_handlers(go, progression=handler)
    assert seen == [("cfg", 4.0, 0.0), ("step", 1.0), ("step", 8.0)]


def test_handler_classes_and_disabled_noop():
    handler = make_progression_handler("my", enable=True, target="file")
    assert handler.classes[:3] == (
        "my_progression_handler",
        "progression_handler",
        "calling_handler",
    )
    disabled = make_progression_handler("off", enable=False, target="file")
    assert disabled(progression(type="update")) is None
    assert disabled.classes[0] == "off_progression_handler"


def test_handlers_register_append_and_lookup():
    set_option("progressr.handlers", None)
    default = handlers()
    assert len(default) == 1
    assert default[0]().classes[0] == "txtprogressbar_progression_handler"

    def update(config, state, progression, **_kwargs):
        return None

    first = _recording(update=update)
    second = make_progression_handler("other", enable=True, target="file")
    previous = handlers(rec=first)
    assert len(previous) == 0
    current = handlers()
    assert len(current) == 1
    assert current._names == ["rec"]
    assert current[0] is first
    appended = handlers(extra=second, append=True)
    assert len(appended) == 1
    assert len(handlers()) == 2
    assert handlers()._names == ["rec", "extra"]

    import sys

    def handler_alpha(progression):
        return None

    sys.modules["progressr.handlers"].handler_alpha = handler_alpha
    set_option("progressr.handlers", None)
    handlers("alpha")
    assert handlers()[0] is handler_alpha
    with pytest.raises(ProgressrError, match="No such progression handler found: \u2018nope\u2019"):
        handlers("nope")
    set_option("progressr.handlers", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        handlers("missing", on_missing="w")
    assert caught
    assert "Ignoring non-existing progression handler" in str(caught[0].message)
    assert handlers() == []

    def rejected(progression):
        return None

    rejected.validator = lambda: False

    def kept(progression):
        return None

    set_option("progressr.handlers", None)
    handlers([rejected, kept])
    assert handlers() == [kept]
    assert handlers(global_=float("nan")) is False
    assert handlers(global_=True) is True
    assert handlers(global_=float("nan")) is True
    handlers(global_=False)
    assert handlers(global_=float("nan")) is False


def test_with_progress_sum_and_without():
    seen = []

    def initiate(config, state, progression, **_kwargs):
        seen.append((progression["type"], state["step"], config["max_steps"], condition_message(progression)))

    def update(config, state, progression, **_kwargs):
        seen.append((progression["type"], state["step"], config["max_steps"], condition_message(progression)))

    handler = _recording(initiate=initiate, update=update)

    def work():
        progress = progressor(along=range(1, 6))
        total = 0
        for value in range(1, 6):
            total += value
            progress(message=str(value))
        return total

    assert with_progress(
        work,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    ) == 15
    assert [item[0] for item in seen] == ["initiate", "update", "update", "update", "update", "update"]
    assert [item[3] for item in seen] == ["", "1", "2", "3", "4", "5"]

    outer = []
    listener = _recording(
        initiate=lambda **_kwargs: outer.append("i"),
        update=lambda **_kwargs: outer.append("u"),
    )

    def wrapped():
        return without_progress(work)

    assert with_calling_handlers(wrapped, progression=listener) == 15
    assert outer == []


def test_too_many_progressions_warns_and_interrupt_reraises():
    handler = _recording()

    def too_many():
        progress = progressor(steps=1)
        progress(message="a")
        progress(message="b")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with_progress(
            too_many,
            handlers=handler,
            enable=True,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    assert caught
    text = str(caught[0].message)
    assert "with_progress() received a progression \u2018update\u2019 request (amount=1; msg=\u2018b\u2019)" in text

    got = []
    interrupting = _recording(
        interrupt=lambda config, state, progression, **_kwargs: got.append(condition_message(progression))
    )

    def boom():
        progress = progressor(steps=3)
        progress(message="a")
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        with_progress(
            boom,
            handlers=interrupting,
            enable=True,
            interrupts=True,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    assert got == ["Progress interrupted by error condition: boom"]


def test_terminal_target_delays_stdout_and_messages(capsys):
    from progressr.condition import message

    handler = make_progression_handler(
        "rec",
        reporter={"initiate": lambda **_kwargs: None, "update": lambda **_kwargs: None},
        enable=True,
        target="terminal",
        interval=0,
    )

    def body():
        progress = progressor(steps=1)
        print("user-out")
        message("user-msg")
        progress(message="a")
        return 7

    assert with_progress(body, handlers=handler, enable=True, interval=0) == 7
    captured = capsys.readouterr()
    assert captured.out == "user-out\n"
    assert captured.err == "user-msg\n"


def test_second_progressor_finishes_the_first():
    seen = []
    handler = _recording(
        initiate=lambda config, state, progression, **_kwargs: seen.append(("I", config["max_steps"])),
        update=lambda config, state, progression, **_kwargs: seen.append(
            ("U", state["step"], condition_message(progression))
        ),
        finish=lambda config, state, progression, **_kwargs: seen.append(("F", progression["type"])),
    )

    def body():
        first = progressor(steps=2)
        first(message="a")
        second = progressor(steps=2)
        second(message="b")
        return 1

    with_progress(
        body,
        handlers=handler,
        enable=True,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    assert ("U", 1.0, "a") in seen
    assert ("F", "finish") in seen
    assert ("U", 1.0, "b") in seen
