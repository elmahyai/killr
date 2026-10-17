"""make_progression_handler: the progression calling-handler state machine."""

from __future__ import annotations

import inspect
import math
from datetime import datetime

from progressr.condition import condition_message, inherits
from progressr.options import (
    ProgressrError,
    get_option,
    is_fork_child,
    squote,
    stdin_is_tty,
    stop_if_not,
)


def _as_numeric(value):
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"inf", "+inf", "infinity"}:
            return math.inf
        if token in {"-inf", "-infinity"}:
            return -math.inf
        return float(value)
    raise ProgressrError("value must be numeric")


def _as_logical(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value != 0
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"true", "t"}:
            return True
        if token in {"false", "f"}:
            return False
    return None


def _null_reporter(*_args, **_kwargs):
    return None


_null_reporter.null_function = True


def _is_null_function(fn) -> bool:
    return bool(getattr(fn, "null_function", False))


def _call_reporter(fn, config, state, progression):
    if fn is None:
        return None
    payload = {}
    payload.update(config)
    payload.update(state)
    payload["config"] = config
    payload["state"] = state
    payload["progression"] = progression
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return fn(**payload)
    parameters = signature.parameters
    if any(item.kind == inspect.Parameter.VAR_KEYWORD for item in parameters.values()):
        return fn(**payload)
    accepted = {}
    for name, parameter in parameters.items():
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ) and name in payload:
            accepted[name] = payload[name]
    if accepted:
        return fn(**accepted)
    return fn()


def _seq_length(start, end, length_out):
    """R seq(from, to, length.out=), and length.out is ceiling'd."""
    count = int(math.ceil(float(length_out)))
    if count <= 0:
        raise ProgressrError("length.out must be positive")
    if count == 1:
        return [float(start)]
    step = (float(end) - float(start)) / (count - 1)
    return [float(start) + index * step for index in range(count)]


def _validate(env, label):
    timestamps = env["timestamps"]
    if timestamps is not None and len(timestamps) == 0:
        raise ProgressrError(
            f".validate_internal_state({squote(label)}): "
            f"length(timestamps) == 0L but not is.null(timestamps): {squote(repr(timestamps))}"
        )


def _reporter_args(env, progression):
    _validate(env, "reporter_args() ... begin")
    timestamps = env["timestamps"]
    if not env["enabled"] and timestamps is not None and len(timestamps) > 0:
        first = timestamps[0]
        if isinstance(first, datetime):
            now = datetime.now(first.tzinfo)
            elapsed = (now - first).total_seconds()
            env["enabled"] = elapsed >= env["enable_after"]
    config = {
        "max_steps": env["max_steps"],
        "times": env["times"],
        "interval": env["interval"],
        "enable_after": env["enable_after"],
        "auto_finish": env["auto_finish"],
        "clear": env["clear"],
        "target": env["target"],
    }
    step = env["step"]
    prev = env["prev_milestone"]
    if step is None or prev is None:
        delta = 0
    else:
        delta = step - prev
    state = {
        "step": step,
        "message": env["message"],
        "timestamps": timestamps,
        "delta": delta,
        "enabled": env["enabled"],
    }
    _validate(env, "reporter_args() ... end")
    return config, state


def _reset_internal(env) -> None:
    env["active"] = False
    env["max_steps"] = None
    env["step"] = None
    env["message"] = None
    env["auto_finish"] = True
    env["timestamps"] = None
    env["milestones"] = None
    env["prev_milestone"] = None
    env["finished"] = False
    env["enabled"] = False
    env["owner"] = None
    env["done"] = []


def make_progression_handler(
    name,
    reporter=None,
    handler=None,
    enable=None,
    enable_after=None,
    times=None,
    interval=None,
    intrusiveness=1.0,
    clear=None,
    target="terminal",
    **_ignored,
):
    """Build a calling handler. Reporter functions receive config, state, and progression."""
    if enable is None:
        enable = get_option("progressr.enable", stdin_is_tty())
    enable = _as_logical(enable)
    stop_if_not(isinstance(enable, bool))
    if not enable:
        times = 0
    if not isinstance(name, str) or name == "":
        stop_if_not(False)
    stop_if_not(isinstance(name, str) and name != "")
    if reporter is None:
        reporter = {}
    stop_if_not(isinstance(reporter, dict))
    if enable_after is None:
        enable_after = get_option("progressr.enable_after", 0.0)
    if times is None:
        times = get_option("progressr.times", math.inf)
    if interval is None:
        interval = get_option("progressr.interval", 0.0)
    if clear is None:
        clear = get_option("progressr.clear", True)
    enable_after = _as_numeric(enable_after)
    stop_if_not(enable_after == enable_after and enable_after >= 0)
    times = _as_numeric(times)
    stop_if_not(times == times and times >= 0)
    interval = _as_numeric(interval)
    stop_if_not(interval == interval and interval >= 0)
    clear = _as_logical(clear)
    stop_if_not(isinstance(clear, bool))
    if isinstance(target, str):
        target_value = target
    else:
        target_value = tuple(target)
        stop_if_not(all(isinstance(item, str) for item in target_value))
    intrusiveness = _as_numeric(intrusiveness)

    reporter = dict(reporter)
    for key in ("reset", "initiate", "update", "finish", "hide", "unhide", "interrupt"):
        if key not in reporter or reporter[key] is None:
            reporter[key] = _null_reporter

    env = {
        "name": name,
        "enable": enable,
        "enable_after": enable_after,
        "times": times,
        "interval": interval,
        "intrusiveness": intrusiveness,
        "clear": clear,
        "target": target_value,
        "reporter": reporter,
        "active": False,
        "max_steps": None,
        "step": None,
        "message": None,
        "auto_finish": True,
        "timestamps": None,
        "milestones": None,
        "prev_milestone": None,
        "finished": False,
        "enabled": False,
        "owner": None,
        "done": [],
    }

    def reset_reporter(progression):
        config, state = _reporter_args(env, progression)
        _call_reporter(reporter["reset"], config, state, progression)
        _validate(env, "reset_reporter() ... done")

    def initiate_reporter(progression):
        config, state = _reporter_args(env, progression)
        stop_if_not(env["active"] is not True)
        stop_if_not(env["prev_milestone"] is None and env["milestones"] is not None and len(env["milestones"]) > 0)
        _call_reporter(reporter["initiate"], config, state, progression)
        env["active"] = True
        env["finished"] = False
        _validate(env, "initiate_reporter() ... done")

    def update_reporter(progression):
        config, state = _reporter_args(env, progression)
        stop_if_not(env["active"] is True)
        stop_if_not(env["step"] is not None and env["milestones"] is not None and len(env["milestones"]) > 0)
        _call_reporter(reporter["update"], config, state, progression)
        _validate(env, "update_reporter() ... done")

    def hide_reporter(progression):
        config, state = _reporter_args(env, progression)
        if reporter.get("hide") is None:
            return
        _call_reporter(reporter["hide"], config, state, progression)

    def unhide_reporter(progression):
        config, state = _reporter_args(env, progression)
        if reporter.get("unhide") is None:
            return
        _call_reporter(reporter["unhide"], config, state, progression)

    def interrupt_reporter(progression):
        config, state = _reporter_args(env, progression)
        if reporter.get("interrupt") is None:
            return
        _call_reporter(reporter["interrupt"], config, state, progression)

    def update_progress(progression):
        if not env["active"]:
            return env["finished"]
        if progression.get("step") is not None:
            progression["amount"] = progression["step"] - env["step"]
        amount = progression["amount"]
        env["step"] = min(max(env["step"] + amount, 0.0), env["max_steps"])
        stop_if_not(env["step"] >= 0)
        text = condition_message(progression)
        if len(text) > 0:
            env["message"] = text
        step = env["step"]
        if step > 0 and env["timestamps"] is not None:
            index = int(step) - 1
            if 0 <= index < len(env["timestamps"]):
                env["timestamps"][index] = datetime.now().astimezone()
        _validate(env, "type=update")
        milestones = env["milestones"] or []
        reached = len(milestones) > 0 and step >= milestones[0]
        if reached or amount == 0:
            skip = False
            if env["interval"] > 0 and step > 0 and env["timestamps"] is not None:
                prev_index = max(env["prev_milestone"] if env["prev_milestone"] is not None else 0, 1)
                current = env["timestamps"][int(step) - 1] if int(step) - 1 < len(env["timestamps"]) else None
                previous = env["timestamps"][int(prev_index) - 1] if int(prev_index) - 1 < len(env["timestamps"]) else None
                if isinstance(current, datetime) and isinstance(previous, datetime):
                    skip = (current - previous).total_seconds() < env["interval"]
            if not skip:
                update_reporter(progression)
                if amount > 0:
                    env["prev_milestone"] = env["step"]
            if amount > 0:
                env["milestones"] = [item for item in (env["milestones"] or []) if item > env["step"]]
                if env["auto_finish"] and env["step"] == env["max_steps"]:
                    finish_reporter(progression)
        return env["finished"]

    def finish_reporter(progression):
        if env["active"] and not env["finished"]:
            update_progress(progression)
        _reporter_args(env, progression)
        if env["active"] and not env["finished"]:
            update_progress(progression)
            config, state = _reporter_args(env, progression)
            _call_reporter(reporter["finish"], config, state, progression)
        _reset_internal(env)
        env["finished"] = True
        _validate(env, "finish_reporter() ... done")

    def is_owner(progression) -> bool:
        progressor_id = progression.get("progressor_uuid")
        if env["owner"] is None:
            env["owner"] = progressor_id
        return env["owner"] == progressor_id

    def is_duplicated(progression) -> bool:
        progressor_id = progression.get("session_uuid")
        index = progression.get("progression_index")
        stamp = progression.get("progression_time")
        index_text = "0" if index is None else str(int(index)) if isinstance(index, (int, float)) and not isinstance(index, bool) else str(index)
        progression_id = f"{progressor_id}-{index_text}-{stamp}"
        if progression_id in env["done"]:
            return True
        env["done"].append(progression_id)
        return False

    def _machine(progression):
        stop_if_not(inherits(progression, "progression"))
        if is_fork_child():
            return False
        if inherits(progression, "control_progression"):
            kind = progression.get("type")
            if kind == "reset":
                _reset_internal(env)
                reset_reporter(progression)
            elif kind == "shutdown":
                finish_reporter(progression)
            elif kind == "hide":
                hide_reporter(progression)
            elif kind == "unhide":
                unhide_reporter(progression)
            elif kind == "interrupt":
                interrupt_reporter(progression)
            else:
                raise ProgressrError(f"Unknown 'control_progression' type: {squote(kind)}")
            return env["finished"]
        if not is_owner(progression):
            return env["finished"]
        duplicated = is_duplicated(progression)
        kind = progression.get("type")
        if duplicated:
            return env["finished"]
        if env["active"] and env["finished"]:
            return env["finished"]
        if kind == "initiate":
            if env["active"]:
                return env["finished"]
            env["max_steps"] = progression.get("steps")
            max_steps = env["max_steps"]
            stop_if_not(isinstance(max_steps, (int, float)) and not isinstance(max_steps, bool))
            stop_if_not(max_steps >= 0)
            max_steps = float(max_steps)
            env["max_steps"] = max_steps
            auto = progression.get("auto_finish")
            env["auto_finish"] = True if auto is None else bool(auto)
            # Scaled times and interval are local to this branch, as in the R handler.
            # config$times and the interval skip keep the original arguments.
            local_times = min(env["times"], max_steps)
            scaled = local_times / env["intrusiveness"] if env["intrusiveness"] not in (0, 0.0) else math.inf
            if isinstance(scaled, float) and math.isnan(scaled):
                local_times = max_steps
            else:
                local_times = min(scaled, max_steps)
            local_times = max(local_times, 1.0)
            _local_interval = env["interval"] * env["intrusiveness"]
            del _local_interval
            if local_times == 1:
                env["milestones"] = [max_steps]
            elif local_times == 2:
                env["milestones"] = [0.0, max_steps]
            else:
                env["milestones"] = _seq_length(0.0, max_steps, local_times + 1.0)[1:]
            count = int(max_steps) if float(max_steps).is_integer() else int(math.ceil(max_steps))
            env["timestamps"] = [None] * max(count, 0)
            if count == 0:
                env["timestamps"] = [datetime.now().astimezone()]
            elif env["timestamps"]:
                env["timestamps"][0] = datetime.now().astimezone()
            env["step"] = 0.0
            env["message"] = ""
            initiate_reporter(progression)
            env["prev_milestone"] = env["step"]
        elif kind == "finish":
            finish_reporter(progression)
        elif kind == "update":
            update_progress(progression)
        elif kind in {"reset", "shutdown", "hide", "unhide", "interrupt"}:
            raise ProgressrError(
                "Unsupported 'progression' type. Was it meant to be a "
                f"'control_progression' condition?: {squote(kind)}"
            )
        else:
            raise ProgressrError(f"Unknown 'progression' type: {squote(kind)}")
        return bool(env["finished"])

    if times == 0 or math.isinf(interval) or math.isinf(intrusiveness):
        def handler(_progression):
            return None
    elif handler is None:
        handler = _machine
    else:
        # A custom handler still carries the configuration environment.
        pass

    if handler is None:
        handler = _machine

    classes = (f"{name}_progression_handler", "progression_handler", "calling_handler", "function")
    handler.classes = classes
    handler._env = env
    handler.enable = enable
    handler.null_function = False
    return handler
