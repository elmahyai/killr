"""Chunk callbacks. Pass a function; these classes are the R6 ones."""

from __future__ import annotations

import inspect

from readr.read import Table


class ChunkCallback:
    def __init__(self, callback=None):
        self.callback = callback

    def receive(self, data, index):
        return None

    def continue_(self):
        return True

    def result(self):
        return None

    def finally_(self):
        return None


class SideEffectChunkCallback(ChunkCallback):
    def __init__(self, callback):
        _require(callback, 2, "`callback` must have two or more arguments")
        super().__init__(callback)
        self._cancel = False

    def receive(self, data, index):
        result = self.callback(data, index)
        self._cancel = result is False

    def continue_(self):
        return not self._cancel


class DataFrameCallback(ChunkCallback):
    def __init__(self, callback):
        _require(callback, 2, "`callback` must have two or more arguments")
        super().__init__(callback)
        self._results = []

    def receive(self, data, index):
        self._results.append(self.callback(data, index))

    def result(self):
        frames = [frame for frame in self._results if frame is not None]
        if not frames:
            return Table([], [], 0)
        return _stack(frames)

    def finally_(self):
        self._results = []


class ListCallback(ChunkCallback):
    def __init__(self, callback):
        _require(callback, 2, "`callback` must have two or more arguments")
        super().__init__(callback)
        self._results = []

    def receive(self, data, index):
        self._results.append(self.callback(data, index))

    def result(self):
        return list(self._results)

    def finally_(self):
        self._results = []


class AccumulateCallback(ChunkCallback):
    def __init__(self, callback, acc=None):
        _require(callback, 3, "`callback` must have three or more arguments")
        super().__init__(callback)
        self.acc = acc

    def receive(self, data, index):
        self.acc = self.callback(data, index, self.acc)

    def result(self):
        return self.acc


def _require(callback, needed, message):
    if not callable(callback):
        raise TypeError(message)
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    ]
    if any(parameter.kind == parameter.VAR_POSITIONAL for parameter in signature.parameters.values()):
        return
    if len(positional) < needed:
        raise TypeError(message)


def as_chunk_callback(value):
    if isinstance(value, ChunkCallback):
        return value
    if callable(value):
        return SideEffectChunkCallback(value)
    raise TypeError("callback must be a function or a chunk callback")


def _stack(frames):
    first = frames[0]
    if not hasattr(first, "names"):
        return frames
    names = list(first.names)
    columns = [[] for _ in names]
    for frame in frames:
        for index, column in enumerate(frame.columns):
            columns[index].extend(list(column))
    return Table(names, columns, sum(frame.nrow for frame in frames), getattr(first, "spec", None), [])


def run_chunks(frame, callback, chunk_size):
    callback = as_chunk_callback(callback)
    try:
        if hasattr(frame, "nrow"):
            total = frame.nrow
            position = 1
            start = 0
            while start < total:
                stop = min(total, start + int(chunk_size))
                piece = Table(
                    list(frame.names),
                    [list(column[start:stop]) for column in frame.columns],
                    stop - start,
                    frame.spec,
                    [],
                )
                callback.receive(piece, position)
                if not callback.continue_():
                    break
                position += stop - start
                start = stop
        else:
            callback.receive(frame, 1)
        return callback.result()
    finally:
        callback.finally_()


def read_delim_chunked(file, callback, delim=None, chunk_size=10000, **kwargs):
    from readr.read import read_delim

    kwargs.setdefault("show_col_types", False)
    frame = read_delim(file, delim=delim, **kwargs)
    return run_chunks(frame, callback, chunk_size)


def read_csv_chunked(file, callback, chunk_size=10000, **kwargs):
    from readr.read import read_csv

    kwargs.setdefault("show_col_types", False)
    frame = read_csv(file, **kwargs)
    return run_chunks(frame, callback, chunk_size)


def read_csv2_chunked(file, callback, chunk_size=10000, **kwargs):
    from readr.read import read_delim

    kwargs.setdefault("show_col_types", False)
    frame = read_delim(file, delim=";", **kwargs)
    return run_chunks(frame, callback, chunk_size)


def read_tsv_chunked(file, callback, chunk_size=10000, **kwargs):
    from readr.read import read_tsv

    kwargs.setdefault("show_col_types", False)
    frame = read_tsv(file, **kwargs)
    return run_chunks(frame, callback, chunk_size)
