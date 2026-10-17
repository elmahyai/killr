"""Forward child progression updates to one parent progressor."""

from __future__ import annotations

from progressr.condition import inherits, try_invoke_restart
from progressr.evaluate import with_progress
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError, get_option, squote, stop_if_not


def progress_aggregator(progress):
    """Return a callable that runs an expression and relays its updates."""
    stop_if_not(inherits(progress, "progressor"))
    # The R function reads this and does not use it further.
    max_steps = progress.steps

    busy = {"value": False}

    def handler(p):
        # R does not re-enter a calling handler that is already running.
        # signal_condition walks every handler, so a parent update signaled
        # from here would be forwarded again. Return and let that signal
        # continue to the outer handlers.
        if busy["value"]:
            return None
        busy["value"] = True
        debug = False
        kind = None
        try:
            stop_if_not(inherits(p, "progression"))
            kind = p["type"]
            debug = bool(get_option("progressr.debug", False))
            if debug:
                from progressr.condition import message as r_message

                r_message(f"Progression handler {squote(kind)} ...")
            if kind == "initiate":
                pass
            elif kind == "finish":
                pass
            elif kind == "reset":
                pass
            elif kind == "shutdown":
                pass
            elif kind == "update":
                progress(child=p)
            elif kind in {"reset", "shutdown", "hide", "unhide", "interrupt"}:
                raise ProgressrError(
                    "Unsupported 'progression' type. Was it meant to be a "
                    f"'control_progression' condition?: {squote(kind)}"
                )
            else:
                raise ProgressrError(f"Unknown 'progression' type: {squote(kind)}")
            try_invoke_restart("muffleProgression")
            return None
        finally:
            if debug and kind is not None:
                from progressr.condition import message as r_message

                r_message(f"Progression handler {squote(kind)} ... done")
            busy["value"] = False

    handler = make_progression_handler("progress_aggregator", handler=handler)

    def fcn(expr):
        return with_progress(expr, handlers=handler)

    fcn.classes = ("progress_aggregator", "function")
    fcn.max_steps = max_steps
    return fcn
