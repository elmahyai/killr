"""with_output_sink, local_output_sink, with_message_sink, local_message_sink (R's sink.R).

R's sink() diverts connections; here the output stream sys.stdout and the
message stream sys.stderr are replaced. A file given by path is opened and
closed by the sink, as R does.
"""

from __future__ import annotations

import os
import sys

from .factory import local_, with_

_MESSAGE_SINKS = [0]


class _Tee:
    """Write to two streams: split = TRUE."""

    def __init__(self, first, second) -> None:
        self._streams = (first, second)

    def write(self, text: str) -> int:
        for stream in self._streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def _open(new, append: bool):
    if new is None:
        raise ValueError("file cannot be NULL")
    if isinstance(new, (str, bytes, os.PathLike)):
        handle = open(new, "a" if append else "w", encoding="utf-8")
        return handle, handle
    return new, None


def set_output_sink(new, append: bool = False, split: bool = False):
    handle, opened = _open(new, append)
    old = (sys.stdout, opened)
    sys.stdout = _Tee(sys.stdout, handle) if split else handle
    return old


def reset_output_sink(state) -> None:
    previous, opened = state
    sys.stdout.flush()
    sys.stdout = previous
    if opened is not None:
        opened.close()


def set_message_sink(new, append: bool = False):
    if _MESSAGE_SINKS[0]:
        raise RuntimeError("Cannot establish message sink when another sink is active.")
    handle, opened = _open(new, append)
    old = (sys.stderr, opened)
    sys.stderr = handle
    _MESSAGE_SINKS[0] += 1
    return old


def reset_message_sink(state) -> None:
    previous, opened = state
    try:
        sys.stderr.flush()
    finally:
        sys.stderr = previous
        _MESSAGE_SINKS[0] -= 1
        if opened is not None:
            opened.close()


with_output_sink = with_(set_output_sink, reset_output_sink)
local_output_sink = local_(set_output_sink, reset_output_sink)
with_message_sink = with_(set_message_sink, reset_message_sink)
local_message_sink = local_(set_message_sink, reset_message_sink)
