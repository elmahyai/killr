import contextlib
import io
import json
import statistics
import time

import progressr.cli_handlers as handlers
from progressr.cli_handlers import handler_cli
from progressr.evaluate import with_progress
from progressr.options import ProgressrError
from progressr.progressor import progressor

_calls = []
_real = handlers.cli_progress_bar


def _spy(*args, **kwargs):
    result = _real(*args, **kwargs)
    _calls.append("id" if isinstance(result, str) and not result.startswith("NA") else "NA")
    return result


handlers.cli_progress_bar = _spy


def _capture(fn):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        fn()
    return buf.getvalue()


def _run(steps, clear, type="steps", show_after=0.0, enable_after=None):
    _calls.clear()
    kwargs = {"type": type, "clear": clear, "enable": True, "show_after": show_after}
    if enable_after is not None:
        kwargs["enable_after"] = enable_after

    def go():
        handler = handler_cli(**kwargs)

        def body():
            progress = progressor(steps=steps, on_exit=False)
            if steps > 0:
                for index in range(1, steps + 1):
                    progress(message=f"m{index}")

        with_progress(
            body,
            handlers=handler,
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )

    err = _capture(go)
    return {"called": bool(_calls), "err": err}


def _formats(type):
    try:
        args = handler_cli(type=type, enable=True).backend_args
    except ProgressrError as exc:
        return {"error": str(exc)}
    return {"format": args.get("format"), "format_done": args.get("format_done")}


def one():
    custom = handler_cli(type="steps", format="CUSTOM", enable=True).backend_args
    try:
        handler_cli(type="nope")
        bad = ""
    except ProgressrError as exc:
        bad = str(exc)
    return {
        "default": _formats("default"),
        "steps": _formats("steps"),
        "percent": _formats("percent"),
        "time": _formats("time"),
        "prefix": _formats("st"),
        "custom_format": custom.get("format"),
        "custom_done": custom.get("format_done"),
        "bad_type": bad,
        "zero": _run(0, False, "default"),
        "show_called": _run(2, False, "time", show_after=1000)["called"],
        "after": _run(2, False, "time", enable_after=1000),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
