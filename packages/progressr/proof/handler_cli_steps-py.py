import contextlib
import io
import json
import statistics
import time

import progressr.cli_handlers as handlers
from progressr.cli_handlers import handler_cli
from progressr.evaluate import with_progress
from progressr.progressor import progressor

_calls = []
_real = handlers.cli_progress_bar


def _spy(*args, **kwargs):
    result = _real(*args, **kwargs)
    _calls.append(result)
    return result


handlers.cli_progress_bar = _spy


def one():
    _calls.clear()
    buf = io.StringIO()

    def body():
        progress = progressor(steps=4, on_exit=False)
        for index in range(1, 5):
            progress(message=f"m{index}")

    with contextlib.redirect_stderr(buf):
        handler = handler_cli(type="steps", clear=False, enable=True)
        with_progress(
            body,
            handlers=handler,
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    ident = _calls[0] if _calls else ""
    return {
        "called": bool(_calls),
        "id": "id" if isinstance(ident, str) and ident.startswith("cli-") else ident,
        "err": buf.getvalue(),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value, ensure_ascii=False))
