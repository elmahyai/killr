"""progressor(): a function that signals progression conditions."""

from __future__ import annotations

import sys
import weakref

from progressr.condition import progression, signal_condition, with_restarts
from progressr.options import ProgressrError, get_option, stop_if_not
from progressr.uuid import progressor_uuid, session_uuid


_MISSING = object()
_PROGRESSOR_COUNT = 0
_FRAME_PROGRESSORS: dict[int, "Progressor"] = {}
_PROFILE_INSTALLED = False
_PREVIOUS_PROFILE = None
_IN_FINISH = False
_GLOBAL_ALLOWED = False

_GLOBAL_ERROR = (
    "A progressor must not be created in the global environment unless "
    "wrapped in a with_progress() or without_progress() call. Alternatively, "
    "create it inside a function or in a local() environment to make sure "
    "there is a finite life span of the progressor"
)
_ON_EXIT_ERROR = (
    "It is not possible to create a progressor in the global environment with on_exit = TRUE"
)


def progressr_in_globalenv(action="query"):
    """Allow a progressor in the module frame while with_progress or without_progress runs."""
    global _GLOBAL_ALLOWED
    action = {"query": "query", "allow": "allow", "disallow": "disallow"}[action]
    if action == "query":
        return _GLOBAL_ALLOWED
    old = _GLOBAL_ALLOWED
    _GLOBAL_ALLOWED = action == "allow"
    return old


def _chain_profile(frame, event, arg):
    previous = _PREVIOUS_PROFILE
    if previous is not None and previous is not _profile:
        return previous(frame, event, arg)
    return None


def _profile(frame, event, arg):
    global _IN_FINISH
    if event == "return" and not _IN_FINISH:
        progressor = _FRAME_PROGRESSORS.pop(id(frame), None)
        if progressor is not None:
            _IN_FINISH = True
            try:
                progressor(type="finish")
            finally:
                _IN_FINISH = False
    return _chain_profile(frame, event, arg)


def _ensure_profile() -> None:
    global _PROFILE_INSTALLED, _PREVIOUS_PROFILE
    if _PROFILE_INSTALLED:
        return
    _PREVIOUS_PROFILE = sys.getprofile()
    sys.setprofile(_profile)
    _PROFILE_INSTALLED = True


def _is_module_frame(frame) -> bool:
    return frame.f_code.co_name == "<module>"


def _signal(condition):
    def go():
        signal_condition(condition)

    with_restarts(go, muffleProgression=lambda _condition: None)
    return condition


class Progressor:
    """Callable progressor. len() is the transformed step count."""

    classes = ("progressor", "function")

    def __init__(self, env, default_message):
        self._env = env
        self._default_message = default_message
        self.enable = True

    def __call__(self, message=_MISSING, type="update", **kwargs):
        env = self._env
        if message is _MISSING:
            message = self._default_message
        env["progression_index"] += 1
        step = kwargs.pop("step", None)
        # `class` is a Python keyword. Callers pass class_ for R's class argument.
        class_ = kwargs.pop("class_", None)
        condition = progression(
            type=type,
            message=message,
            step=step,
            class_=class_,
            progressor_uuid=env["progressor_uuid"],
            progression_index=env["progression_index"],
            owner_session_uuid=env["owner_session_uuid"],
            call=env["call"] if env["trace"] else None,
            calls=env["calls"] if env["trace"] else None,
            **kwargs,
        )
        _signal(condition)
        return condition

    def __len__(self):
        steps = self._env["steps"]
        if isinstance(steps, float) and not steps.is_integer():
            raise TypeError("progressor length is not an integer number of steps")
        return int(steps)

    @property
    def steps(self):
        return self._env["steps"]

    def __repr__(self) -> str:
        env = self._env
        lines = ["progressor:"]
        lines.append(f"- label: {env.get('label')}")
        lines.append(f"- steps: {env.get('steps')}")
        lines.append(f"- initiate: {env.get('initiate')}")
        lines.append(f"- auto_finish: {env.get('auto_finish')}")
        message = env.get("message")
        if callable(message):
            shown = "<a function>"
        else:
            shown = "" if message in (None, ()) else str(message)
        lines.append(f"- default message: {shown}")
        lines.append(f"- call stack: {'<disabled>' if not env.get('trace') else env.get('calls')}")
        lines.append(f"- progressor_uuid: {env.get('progressor_uuid')}")
        lines.append(f"- progressor_count: {env.get('progressor_count')}")
        lines.append(f"- progression_index: {env.get('progression_index')}")
        lines.append(f"- owner_session_uuid: {env.get('owner_session_uuid')}")
        lines.append(f"- enable: {env.get('enable')}")
        import sys

        lines.append(f"- size: {sys.getsizeof(self)} bytes")
        return "\n".join(lines)


class _VoidProgressor:
    """One shared progressor that signals nothing."""

    classes = ("progressor", "function")
    enable = False

    def __call__(self, *args, **kwargs):
        return None

    def __repr__(self) -> str:
        return "progressor:\n- enable: False"


_VOID = _VoidProgressor()


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        stop_if_not(False)
    if isinstance(value, float) and value != value:
        stop_if_not(False)
    return float(value)


def progressor(
    steps=_MISSING,
    along=None,
    offset=0,
    scale=1,
    transform=None,
    message=(),
    label=None,
    trace=False,
    initiate=True,
    finalize=False,
    auto_finish=True,
    on_exit=_MISSING,
    enable=None,
    envir=None,
):
    """Create a progressor. At module level this is an error unless with_progress allowed it."""
    if enable is None:
        enable = get_option("progressr.enable", True)
    stop_if_not(isinstance(enable, bool))
    if not enable:
        return _VOID

    frame = envir if envir is not None else sys._getframe(1)
    is_global = _is_module_frame(frame)
    if on_exit is _MISSING:
        on_exit = not is_global
    stop_if_not(isinstance(on_exit, bool))

    if steps is _MISSING:
        steps = 0 if along is None else len(along)
    if steps is None and along is None:
        stop_if_not(False)
    stop_if_not(isinstance(steps, (int, float)) and not isinstance(steps, bool))
    steps = float(steps)
    stop_if_not(steps == steps and steps >= 0)
    offset = float(offset)
    scale = float(scale)
    stop_if_not(offset == offset)
    stop_if_not(scale == scale)
    if transform is None:
        def transform(steps, scale=scale, offset=offset):
            return scale * steps + offset
    stop_if_not(callable(transform))
    steps = transform(steps)
    stop_if_not(isinstance(steps, (int, float)) and not isinstance(steps, bool))
    steps = float(steps)
    stop_if_not(steps == steps and steps >= 0)
    if label is not None and not isinstance(label, str):
        label = str(label)
    stop_if_not(label is None or isinstance(label, str))

    if is_global:
        if not progressr_in_globalenv("query"):
            raise ProgressrError(_GLOBAL_ERROR)
        if on_exit:
            raise ProgressrError(_ON_EXIT_ERROR)

    global _PROGRESSOR_COUNT
    _PROGRESSOR_COUNT += 1
    env = {
        "progression_index": 0,
        "progressor_uuid": progressor_uuid(_PROGRESSOR_COUNT),
        "owner_session_uuid": session_uuid(attributes=True),
        "progressor_count": _PROGRESSOR_COUNT,
        "enable": True,
        "initiate": initiate,
        "auto_finish": auto_finish,
        "trace": trace,
        "steps": steps,
        "label": label,
        "offset": offset,
        "scale": scale,
        "message": message,
        "call": None,
        "calls": None,
    }
    created = Progressor(env, message)

    previous = _FRAME_PROGRESSORS.get(id(frame))
    if previous is not None:
        previous(type="finish")
        _FRAME_PROGRESSORS.pop(id(frame), None)

    if initiate:
        created(type="initiate", steps=steps, auto_finish=auto_finish)

    if on_exit:
        _FRAME_PROGRESSORS[id(frame)] = created
        _ensure_profile()

    if finalize:
        state = env

        def _shutdown(state=state):
            state["progression_index"] += 1
            condition = progression(
                type="shutdown",
                message=state["message"],
                progressor_uuid=state["progressor_uuid"],
                progression_index=state["progression_index"],
                owner_session_uuid=state["owner_session_uuid"],
                call=None,
                calls=None,
            )
            _signal(condition)

        weakref.finalize(created, _shutdown)

    return created
