"""with_progress and without_progress.

R delays the expression. Python evaluates arguments before the call, so both
functions take a zero-argument callable and call it while the handlers are active.
"""

from __future__ import annotations

from progressr.condition import (
    condition_message,
    control_progression,
    inherits,
    muffle_matching,
    signal_condition,
    try_invoke_restart,
    with_calling_handlers,
    with_restarts,
)
from progressr.delays import delay_stdout as start_stdout_delay
from progressr.delays import flush_conditions, flush_stdout, use_delays
from progressr.handlers import global_progression_handler, handlers as current_handlers
from progressr.options import (
    get_option,
    options_restore,
    options_set,
    squote,
    stop_if_not,
)
from progressr.progressor import progressr_in_globalenv


def _empty_message(progression) -> bool:
    message = progression.get("message")
    if callable(message):
        message = message(progression)
    return message is None or message == () or message == []


def warn_about_too_many_progressions(progression, global_=False):
    """Match the R warning when updates continue after the progressor has finished."""
    import warnings

    amount = progression.get("amount")
    if isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount == 0:
        return
    kind = progression.get("type")
    if isinstance(kind, str) and kind == "finish":
        return
    if _empty_message(progression):
        shown = "character(0)"
    else:
        shown = squote(condition_message(progression))
    if isinstance(amount, float) and amount.is_integer():
        amount_text = str(int(amount))
    else:
        amount_text = format(amount, "g")
    who = "The global progression handlers" if global_ else "with_progress()"
    warnings.warn(
        f"{who} received a progression {squote(kind)} request "
        f"(amount={amount_text}; msg={shown}), but is no longer listening to this "
        "progressor. This can happen when code signals more progress updates than "
        'steps in the progressor. To troubleshoot this, retry with progressr::handlers("debug")',
        stacklevel=2,
    )


def as_progression_handler(handlers, drop=True):
    if not isinstance(handlers, (list, tuple)):
        handlers = [handlers]
    prepared = []
    for handler in handlers:
        stop_if_not(callable(handler))
        if not inherits(handler, "progression_handler"):
            handler = handler()
            stop_if_not(callable(handler))
            stop_if_not(inherits(handler, "progression_handler"))
        if drop:
            env = getattr(handler, "_env", None)
            if env is not None and "enable" in env:
                value = env["enable"]
            else:
                value = getattr(handler, "enable", None)
            if not (value is True or value is None):
                continue
        prepared.append(handler)
    return prepared


def make_calling_handler(handlers):
    if len(handlers) > 1:
        def calling_handler(progression):
            finished = False
            for handler in handlers:
                if handler(progression):
                    finished = True
            return finished

        return calling_handler
    return handlers[0]


def _signal_to(calling, progression):
    def go():
        signal_condition(progression)

    def outer():
        with_restarts(go, muffleProgression=lambda _progression: None)

    with_calling_handlers(outer, progression=calling)


def _maybe_flush_intermediate(delays, calling, conditions, stdout_file, unhide):
    terminal = delays["terminal"]
    if not (bool(terminal) and getattr(terminal, "flush", False)):
        return stdout_file
    from progressr.delays import has_buffered_stdout

    if not conditions and not has_buffered_stdout(stdout_file):
        return stdout_file
    calling(control_progression("hide"))
    stdout_file = flush_stdout(stdout_file, close=False)
    flush_conditions(conditions)
    if unhide:
        calling(control_progression("unhide"))
    return stdout_file


def with_progress(
    expr,
    handlers=None,
    cleanup=True,
    delay_terminal=None,
    delay_stdout=None,
    delay_conditions=None,
    interrupts=None,
    interval=None,
    enable=None,
):
    """Call `expr` with progression handlers active. `expr` is a zero-argument callable."""
    stop_if_not(isinstance(cleanup, bool))
    if interrupts is None:
        interrupts = get_option("progressr.interrupts", True)
    stop_if_not(isinstance(interrupts, bool))
    if handlers is None:
        handlers = current_handlers()
    if not isinstance(handlers, (list, tuple)):
        handlers = [handlers]
    global_progression_handler(False)
    try:
        if len(handlers) == 0:
            return expr()
        if enable is False:
            return expr()
        to_set = {}
        if enable is not None:
            stop_if_not(isinstance(enable, bool))
            to_set["progressr.enable"] = enable
        if interval is not None:
            stop_if_not(isinstance(interval, (int, float)) and not isinstance(interval, bool))
            stop_if_not(interval == interval)
            to_set["progressr.interval"] = float(interval)
        saved = options_set(to_set) if to_set else {}
        try:
            progressr_in_globalenv("allow")
            try:
                prepared = as_progression_handler(handlers)
                if len(prepared) == 0:
                    return expr()
                delays = use_delays(
                    prepared,
                    terminal=delay_terminal,
                    stdout=delay_stdout,
                    conditions=delay_conditions,
                )
                calling = make_calling_handler(prepared)
                status = {"value": "incomplete"}
                finished = {"value": False}
                capture = {"on": True}
                conditions = []
                stdout_file = start_stdout_delay(delays, None)

                def progression_handler(progression):
                    nonlocal stdout_file
                    if progression.get("type") == "initiate":
                        if not finished["value"]:
                            calling(control_progression("shutdown"))
                        finished["value"] = False
                    else:
                        if finished["value"]:
                            warn_about_too_many_progressions(progression)
                            return
                    capture["on"] = False
                    try:
                        stdout_file = _maybe_flush_intermediate(
                            delays, calling, conditions, stdout_file, unhide=True
                        )
                        finished["value"] = bool(calling(progression))
                    finally:
                        capture["on"] = True

                def condition_handler(condition):
                    if not capture["on"] or finished["value"]:
                        return
                    if not inherits(condition, delays["conditions"]):
                        return
                    conditions.append(condition)
                    if inherits(condition, "message"):
                        try_invoke_restart("muffleMessage", condition)
                    elif inherits(condition, "warning"):
                        try_invoke_restart("muffleWarning", condition)
                    else:
                        muffle_matching(condition)

                def handle_failure(exc, kind):
                    nonlocal stdout_file
                    capture["on"] = False
                    try:
                        stdout_file = _maybe_flush_intermediate(
                            delays, calling, conditions, stdout_file, unhide=False
                        )
                        if interrupts:
                            text = f"Progress interrupted by {kind} condition: {exc}"
                            calling(control_progression("interrupt", message=text))
                    finally:
                        capture["on"] = True

                try:
                    def run():
                        return expr()

                    try:
                        result = with_calling_handlers(
                            run,
                            progression=progression_handler,
                            interrupt=lambda condition: handle_failure(condition, "interrupt"),
                            error=lambda condition: handle_failure(condition, "error"),
                            condition=condition_handler,
                        )
                    except KeyboardInterrupt as exc:
                        handle_failure(exc, "interrupt")
                        raise
                    except Exception as exc:
                        handle_failure(exc, "error")
                        raise
                    status["value"] = "ok"
                    return result
                finally:
                    if cleanup:
                        _signal_to(calling, control_progression("shutdown", status=status["value"]))
                    flush_stdout(stdout_file, close=True, must_work=True)
                    if delays["conditions"]:
                        flush_conditions(conditions)
            finally:
                progressr_in_globalenv("disallow")
        finally:
            if to_set:
                options_restore(saved)
    finally:
        global_progression_handler(True)


def without_progress(expr):
    """Call `expr` while progression conditions are muffled.

    A progressor may be created in the module frame for the duration of the call.
    """
    progressr_in_globalenv("allow")
    try:
        global_progression_handler(False)
        try:
            def muffle(progression):
                try_invoke_restart("muffleProgression", progression)

            def run():
                return expr()

            return with_calling_handlers(run, progression=muffle)
        finally:
            global_progression_handler(True)
    finally:
        progressr_in_globalenv("disallow")
