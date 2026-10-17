import contextlib
import io
import json
import re
import statistics
import time

from progressr.evaluate import with_progress
from progressr.progressor import progressor
from progressr.reporters import handler_debug

_LINE = re.compile(
    r"^\[.*?\] \([0-9.]+s => \+[+-]?[0-9.]+s\) ([^:]+): ([0-9.]+)/([0-9.]+) "
    r"\(([+-][^)]*)\) '(.*)' \{clear=([^,]*), enabled=([^,]*), status=(.*)\}"
    r"(?: \[progressor=.*, owner=.*\])?$"
)


def _parse(text):
    events = []
    for line in text.splitlines():
        match = _LINE.match(line)
        if match is None:
            raise RuntimeError(line)
        events.append(
            {
                "type": match.group(1),
                "step": float(match.group(2)),
                "max_steps": float(match.group(3)),
                "delta": float(match.group(4)),
                "message": match.group(5),
                "clear": match.group(6),
                "enabled": match.group(7),
                "status": match.group(8),
                "uuid_suffix": " [progressor=" in line,
            }
        )
    return events


def _run(handler, fn):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        with_progress(
            fn,
            handlers=handler,
            enable=True,
            interval=0,
            delay_terminal=False,
            delay_stdout=False,
            delay_conditions=(),
        )
    return _parse(err.getvalue())


def one():
    def plain():
        progress = progressor(steps=4, on_exit=False)
        progress(message="one")
        progress(message="two", amount=0, class_="sticky")
        progress(message="halt", amount=0, type="interrupt", class_="control_progression")
        progress(message="three")
        progress(message="four")

    def marked():
        progress = progressor(steps=1, on_exit=False)
        progress(message="z")

    events = _run(handler_debug(enable=True, uuid=False), plain)
    uuid_events = _run(handler_debug(enable=True, uuid=True), marked)
    for item in events:
        item.pop("uuid_suffix")
    suffix = all(item.pop("uuid_suffix") for item in uuid_events)
    return {"events": events, "uuid_events": uuid_events, "uuid_suffix": suffix}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
