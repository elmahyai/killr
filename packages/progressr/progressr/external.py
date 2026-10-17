"""Handlers that stop when a suggested package is not installed.

beepr, BRRR, notifier, ntfy, pbmcapply, RPushbullet, rstudioapi, and shiny
are not part of this translation. The functions follow the R control flow
until that package lookup fails. They do not play a sound, post a
notification, or open a Shiny session.
"""

from __future__ import annotations

import math
import warnings

from progressr.condition import inherits
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, get_option, squote, stop_if_not
from progressr.progressor import progressor


_MISSING = object()

_MAKE_FORMALS = {
    "name",
    "reporter",
    "handler",
    "enable",
    "enable_after",
    "times",
    "interval",
    "intrusiveness",
    "clear",
    "target",
}

_INPUT_NAMES = ("message", "detail")
_INPUT_SOURCES = ("message", "non_sticky_message", "sticky_message")

_FAKE: dict[str, bool] = {}
_RPUSHBULLET = {"res": None}


def _missing_package(name: str) -> None:
    """R `pkg::name` when the package is not installed."""
    raise ProgressrError(f"there is no package called {squote(name)}")


def _is_fake(name: str) -> bool:
    """progressr.tests.fake_handlers, cached the way is_fake() caches it."""
    if name in _FAKE:
        return _FAKE[name]
    option = get_option("progressr.tests.fake_handlers", None)
    if option is None:
        fake = False
    elif isinstance(option, str):
        fake = name == option
    else:
        fake = name in option
    _FAKE[name] = fake
    return fake


def _option_number(value, option: str, default):
    if value is None:
        value = get_option(option, default)
    return value


def _r_length(value) -> int:
    """R length() for the values these handlers inspect."""
    if value is None:
        return 0
    if isinstance(value, (str, bytes)):
        return 1
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _handler_backend_args(*args, **kwargs):
    """Drop make_progression_handler arguments. Unnamed extras are an error."""
    if args:
        raise ProgressrError("Additional arguments must be named")
    if not kwargs:
        return {}
    names = list(kwargs)
    if any(not name for name in names):
        raise ProgressrError("Additional arguments must be named")
    return {name: value for name, value in kwargs.items() if name not in _MAKE_FORMALS}


def _input_values(value):
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return list(value)
    return value


def _each_input_ok(inputs) -> bool:
    for value in inputs.values():
        if value is None:
            continue
        items = _input_values(value)
        if not isinstance(items, list):
            return False
        if any(not isinstance(item, str) or item not in _INPUT_SOURCES for item in items):
            return False
    return True


def _validate_shiny_inputs(inputs) -> None:
    stop_if_not(isinstance(inputs, dict))
    stop_if_not(isinstance(inputs, dict))
    stop_if_not(all(name in _INPUT_NAMES for name in inputs))
    stop_if_not(_each_input_ok(inputs))


def _expand_inputs(inputs):
    """'message' means both the sticky and the non-sticky source."""
    expanded = {}
    for name, value in inputs.items():
        items = _input_values(value)
        if items is None:
            expanded[name] = None
            continue
        if "message" in items:
            items = [item for item in items if item != "message"]
            items.extend(["non_sticky_message", "sticky_message"])
        unique = []
        for item in items:
            if item not in unique:
                unique.append(item)
        expanded[name] = unique
    return expanded


def _assert_max_steps(config) -> None:
    max_steps = config["max_steps"]
    stop_if_not(_r_length(max_steps) == 1)
    stop_if_not(not isinstance(max_steps, bool) and isinstance(max_steps, (int, float)))
    stop_if_not(max_steps == max_steps)
    stop_if_not(math.isfinite(float(max_steps)))
    stop_if_not(float(max_steps) >= 0)


def _require_namespace(package: str) -> bool:
    """These suggested packages are not installed and are not translated."""
    return False


def _named_items(handlers):
    if handlers is None:
        return []
    if isinstance(handlers, dict):
        return list(handlers.items())
    names = list(getattr(handlers, "_names", []))
    values = list(handlers)
    if len(names) != len(values):
        names = [None] * len(values)
    return list(zip(names, values))


def _default_shiny_handlers():
    """c(shiny = handler_shiny, handlers(default = NULL)), and c() drops NULL."""
    current = get_option("progressr.handlers", None)
    items = [("shiny", handler_shiny)]
    if current is None:
        return items
    items.extend(_named_items(current))
    return items


def _commaq(values) -> str:
    return ", ".join(squote(value) for value in values)


def _apply_input_attribute(inputs, message, detail):
    for name, value in (("message", message), ("detail", detail)):
        if value is None:
            continue
        raw = getattr(value, "input", None)
        if raw is None:
            continue
        items = _input_values(raw)
        if items is None:
            continue
        unique = []
        for item in items:
            if item not in unique:
                unique.append(item)
        unknown = [item for item in unique if item not in _INPUT_SOURCES]
        if unknown:
            raise ProgressrError(
                "Unknown value of attribute "
                f"{squote('input')} on argument {squote(name)}: {_commaq(unknown)}"
            )
        inputs[name] = unique
    return inputs


def is_rpushbullet_working(quiet=True) -> bool:
    """FALSE when RPushbullet is not installed. The warning is not cached."""
    if _RPUSHBULLET["res"] is not None and not (isinstance(_RPUSHBULLET["res"], float) and math.isnan(_RPUSHBULLET["res"])):
        return bool(_RPUSHBULLET["res"])
    if not _require_namespace("RPushbullet"):
        warnings.warn(f"Package {squote('RPushbullet')} is not installed", stacklevel=2)
        return False
    return False


def _silence(sound) -> bool:
    """R is.na(sound): a missing sound index plays nothing."""
    if sound is None:
        return True
    if isinstance(sound, float) and math.isnan(sound):
        return True
    return False


def _audio_handler(name, sounds, intrusiveness, target, **extra):
    """Reporter conditions from handler_beepr and handler_brrr. The backend is absent."""

    def play(sound):
        if _silence(sound):
            return None
        return None

    def initiate(config, state, progression=None, **kwargs):
        if not state["enabled"] or config["times"] == 1:
            return None
        return play(sounds["initiate"])

    def interrupt(config, state, progression=None, **kwargs):
        return play(sounds["interrupt"])

    def update(config, state, progression, **kwargs):
        if not state["enabled"] or progression["amount"] == 0 or config["times"] <= 2:
            return None
        return play(sounds["update"])

    def finish(config, state, progression=None, **kwargs):
        if not state["enabled"]:
            return None
        return play(sounds["finish"])

    return make_progression_handler(
        name,
        reporter={
            "initiate": initiate,
            "interrupt": interrupt,
            "update": update,
            "finish": finish,
        },
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def handler_beepr(
    initiate=2,
    update=10,
    finish=11,
    interrupt=9,
    intrusiveness=None,
    target="audio",
    *args,
    **extra,
):
    """Progression handler for beepr::beep(). The package lookup fails first."""
    del args
    if not _is_fake("handler_beepr"):
        _missing_package("beepr")
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.audio", 5.0)
    return _audio_handler(
        "beepr",
        {"initiate": initiate, "update": update, "finish": finish, "interrupt": interrupt},
        intrusiveness,
        target,
        **extra,
    )


def handler_brrr(
    initiate="takeoff",
    update="bigsean4",
    finish="khaled3",
    interrupt="busta",
    intrusiveness=None,
    target="audio",
    *args,
    **extra,
):
    """Progression handler for BRRR::skrrrahh(). requireNamespace stops first."""
    del args
    if not _is_fake("handler_brrr"):
        if not _require_namespace("BRRR"):
            raise ProgressrError(
                "Package 'BRRR' is not available. "
                "See ?progressr::handler_notifier() for installation instructions"
            )
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.audio", 5.0)
    return _audio_handler(
        "brrr",
        {"initiate": initiate, "update": update, "finish": finish, "interrupt": interrupt},
        intrusiveness,
        target,
        **extra,
    )


def _progress_notify(title, message, step, max_steps, notifier):
    """Format '[percent] message' and hand it to the notifier. The notifier is absent."""
    stop_if_not(callable(notifier))
    ratio = 1 if max_steps == 0 else step / max_steps
    shown = "" if message is None or message == () or message == [] else message
    if isinstance(shown, (list, tuple)):
        shown = "".join("" if piece is None else str(piece) for piece in shown)
    else:
        shown = "" if shown is None else str(shown)
    notifier(title=title, message=f"[{100 * ratio:.0f}%] {shown}")


def _notify_handler(name, intrusiveness, target, notifier, title=None, **extra):
    finished = {"value": False}

    def reset(config=None, state=None, progression=None, **kwargs):
        finished["value"] = False

    def _send(config, state, message):
        if title is None:
            _progress_notify(
                "R 'progressr' notification",
                message,
                state["step"],
                config["max_steps"],
                notifier,
            )
        else:
            _progress_notify(title, message, state["step"], config["max_steps"], notifier)

    def initiate(config, state, progression=None, **kwargs):
        if not state["enabled"] or config["times"] == 1:
            return None
        _send(config, state, state["message"])

    def interrupt(config, state, progression, **kwargs):
        from progressr.condition import condition_message

        _send(config, state, condition_message(progression))

    def update(config, state, progression, **kwargs):
        if not state["enabled"] or progression["amount"] == 0 or config["times"] <= 2:
            return None
        _send(config, state, state["message"])

    def finish(config, state, progression=None, **kwargs):
        if finished["value"]:
            return None
        if not state["enabled"]:
            return None
        if state["delta"] > 0:
            _send(config, state, state["message"])
        finished["value"] = True

    return make_progression_handler(
        name,
        reporter={
            "reset": reset,
            "initiate": initiate,
            "interrupt": interrupt,
            "update": update,
            "finish": finish,
        },
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def _null_notifier(*args, **kwargs):
    return None


def handler_notifier(intrusiveness=None, target="gui", *args, **extra):
    """Progression handler for notifier::notify(). requireNamespace stops first."""
    del args
    if not _is_fake("handler_notifier"):
        if not _require_namespace("notifier"):
            raise ProgressrError(
                "Package 'notifier' is not available. "
                "See ?progressr::handler_notifier() for installation instructions"
            )
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.notifier", 10)
    return _notify_handler("notifier", intrusiveness, target, _null_notifier, **extra)


def handler_ntfy(intrusiveness=None, target="gui", *args, title="Progress update from R", **extra):
    """Progression handler for ntfy::ntfy_send(). requireNamespace stops first."""
    del args
    if not _is_fake("handler_ntfy"):
        if not _require_namespace("ntfy"):
            raise ProgressrError(
                "Package 'ntfy' is not available. "
                "See ?progressr::handler_ntfy() for installation instructions"
            )
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.ntfy", 5)
    return _notify_handler("ntfy", intrusiveness, target, _null_notifier, title=title, **extra)


def handler_pbmcapply(
    char="=",
    substyle=3,
    style="ETA",
    file=None,
    intrusiveness=None,
    target="terminal",
    *args,
    **extra,
):
    """Progression handler for pbmcapply::progressBar(). The lookup fails after backend args."""
    del file
    _handler_backend_args(char=char, substyle=substyle, style=style, *args, **extra)
    if not _is_fake("handler_pbmcapply"):
        _missing_package("pbmcapply")
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.terminal", 1)
    return make_progression_handler("pbmcapply", intrusiveness=intrusiveness, target=target)


def handler_rpushbullet(
    intrusiveness=None,
    target="gui",
    *args,
    title="Progress update from R",
    recipients=None,
    email=None,
    channel=None,
    apikey=None,
    devices=None,
    **extra,
):
    """Progression handler for RPushbullet::pbPost(). requireNamespace stops first."""
    del args, recipients, email, channel, apikey, devices
    if not _is_fake("handler_rpushbullet"):
        if not _require_namespace("RPushbullet"):
            raise ProgressrError("Package RPushbullet is not available")
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.rpushbullet", 5)
    return _notify_handler("rpushbullet", intrusiveness, target, _null_notifier, title=title, **extra)


handler_rpushbullet.validator = is_rpushbullet_working


def _console_title():
    from datetime import datetime

    return datetime.now().strftime("Console %X")


def handler_rstudio(intrusiveness=None, target="gui", title=_MISSING, **extra):
    """Progression handler for the RStudio job. rstudioapi is resolved on initiate."""
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.gui", 1)
    if title is _MISSING:
        title = _console_title
    job_id = {"value": None}

    def initiate(config, state, progression=None, **kwargs):
        if not state["enabled"] or config["times"] <= 2:
            return None
        name = state["message"]
        if _r_length(name) == 0:
            if title is None:
                name = "Console"
            elif isinstance(title, str):
                name = title
            elif callable(title):
                name = title()
        stop_if_not(job_id["value"] is None)
        stop_if_not(isinstance(name, str))
        stop_if_not(_r_length(name) == 1)
        _missing_package("rstudioapi")

    def update(config, state, progression=None, **kwargs):
        if not state["enabled"] or config["times"] <= 2:
            return None
        if state["delta"] < 0 or state["delta"] == 0:
            return None
        stop_if_not(job_id["value"] is not None)
        _missing_package("rstudioapi")

    def finish(config=None, state=None, progression=None, **kwargs):
        if job_id["value"] is not None:
            _missing_package("rstudioapi")
        job_id["value"] = None
        return None

    return make_progression_handler(
        "rstudio",
        reporter={"initiate": initiate, "update": update, "finish": finish},
        intrusiveness=intrusiveness,
        target=target,
        **extra,
    )


def handler_shiny(
    intrusiveness=None,
    target="gui",
    inputs=None,
    enable=_MISSING,
    **extra,
):
    """Progression handler for shiny::incProgress(). The lookup happens on update."""
    intrusiveness = _option_number(intrusiveness, "progressr.intrusiveness.gui", 1)
    if inputs is None:
        inputs = {"message": None, "detail": "message"}
    if enable is _MISSING:
        enable = get_option("progressr.enable", True)
    _validate_shiny_inputs(inputs)
    inputs = _expand_inputs(inputs)

    def interrupt(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        _assert_max_steps(config)
        _missing_package("shiny")

    def update(config, state, progression, **kwargs):
        if not state["enabled"]:
            return None
        _assert_max_steps(config)
        _missing_package("shiny")

    return make_progression_handler(
        "shiny",
        reporter={"interrupt": interrupt, "update": update},
        intrusiveness=intrusiveness,
        target=target,
        enable=enable,
        **extra,
    )


def with_progress_shiny(
    expr,
    *args,
    message=None,
    detail=None,
    inputs=None,
    env=None,
    quoted=False,
    handlers=_MISSING,
    **kwargs,
):
    """withProgressShiny(). shiny::withProgress is resolved before expr runs."""
    del args, env, kwargs
    if inputs is None:
        inputs = {"message": None, "detail": "message"}
    else:
        inputs = dict(inputs)
    # quoted = FALSE captures expr with substitute(). Either way it is not evaluated yet.
    delayed = expr
    del delayed
    stop_if_not(isinstance(inputs, dict))
    stop_if_not(all(name in _INPUT_NAMES for name in inputs))
    if handlers is _MISSING:
        handlers = _default_shiny_handlers()
    else:
        handlers = _named_items(handlers)
    names = [name for name, _handler in handlers]
    stop_if_not("shiny" in names)
    if names.count("shiny") > 1:
        warnings.warn("Detected a 'shiny' handler set via progressr::handlers()")
    inputs = _apply_input_attribute(inputs, message, detail)
    _validate_shiny_inputs(inputs)
    for name, handler in handlers:
        if name == "shiny" and callable(handler) and not inherits(handler, "progression_handler"):
            # formals(handler_shiny)$inputs is a call, so identical() is false.
            # R rewrites that local copy, then looks up shiny::withProgress.
            break
    del quoted
    _missing_package("shiny")


def progress_progressr(*args, **kwargs):
    """plyr .progress callbacks. init, step, and term signal one progressor."""
    del args, kwargs
    box = {"progress": None}

    def init(x, *ignored, **extra):
        del ignored, extra
        box["progress"] = progressor(x, on_exit=False)

    def step():
        box["progress"]()

    def term():
        box["progress"](type="finish")

    return {"init": init, "step": step, "term": term}
