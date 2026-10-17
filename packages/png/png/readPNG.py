"""Read a PNG the way the R package png 0.1-9 reads one.

The pixels come from the system libpng through a small C wrapper. libpng
longjmps on error, so that jump stays in the wrapper and ctypes only sees
the returned struct.
"""

from __future__ import annotations

import ctypes
import math
import os
import subprocess
import warnings
from pathlib import Path

import numpy as np

from png._unserialize import unserialize

_TRUE = {"T", "TRUE", "True", "true"}
_FALSE = {"F", "FALSE", "False", "false"}
_NA_INT = -2147483648
_LIB = None


class PNGError(Exception):
    """An error from readPNG, with R's message."""


class NamedCharacter:
    """A character vector and the names readPNG keeps on the text tag."""

    def __init__(self, pairs):
        self.pairs = [(name, value) for name, value in pairs]

    @property
    def names(self):
        return [name for name, _value in self.pairs]

    def __iter__(self):
        return iter(self.pairs)

    def __len__(self):
        return len(self.pairs)

    def __repr__(self) -> str:
        return f"NamedCharacter({self.pairs!r})"


class PNGImage(np.ndarray):
    """An image array. ``info`` and ``metadata`` follow readPNG's attributes."""

    def __new__(cls, data, info=None, metadata=None, channels=None):
        obj = np.asarray(data).view(cls)
        obj.info = info
        obj.metadata = metadata
        obj.channels = channels
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.info = getattr(obj, "info", None)
        self.metadata = getattr(obj, "metadata", None)
        self.channels = getattr(obj, "channels", None)


class _Result(ctypes.Structure):
    _fields_ = [
        ("samples", ctypes.POINTER(ctypes.c_double)),
        ("native_pixels", ctypes.POINTER(ctypes.c_int32)),
        ("text_keys", ctypes.POINTER(ctypes.c_char_p)),
        ("text_vals", ctypes.POINTER(ctypes.c_char_p)),
        ("text_key_na", ctypes.POINTER(ctypes.c_int)),
        ("text_val_na", ctypes.POINTER(ctypes.c_int)),
        ("gamma", ctypes.c_double),
        ("dpi_x", ctypes.c_double),
        ("dpi_y", ctypes.c_double),
        ("asp", ctypes.c_double),
        ("ok", ctypes.c_int),
        ("height", ctypes.c_int),
        ("width", ctypes.c_int),
        ("planes", ctypes.c_int),
        ("native_mode", ctypes.c_int),
        ("n_samples", ctypes.c_int),
        ("channels", ctypes.c_int),
        ("has_info", ctypes.c_int),
        ("info_width", ctypes.c_int),
        ("info_height", ctypes.c_int),
        ("info_bit_depth", ctypes.c_int),
        ("color_is_int", ctypes.c_int),
        ("color_int", ctypes.c_int),
        ("has_gamma", ctypes.c_int),
        ("has_dpi", ctypes.c_int),
        ("has_asp", ctypes.c_int),
        ("ntext", ctypes.c_int),
        ("error", ctypes.c_char * 1024),
        ("warning", ctypes.c_char * 2048),
        ("color_type", ctypes.c_char * 64),
    ]


def _library():
    global _LIB
    if _LIB is not None:
        return _LIB
    here = Path(__file__).resolve().parent
    source = here / "_readpng.c"
    binary = here / "_readpng.so"
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        subprocess.check_call(
            ["gcc", "-shared", "-fPIC", "-O2", "-o", str(binary), str(source), "-lpng"],
        )
    lib = ctypes.CDLL(str(binary))
    lib.readpng_read.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(_Result),
    ]
    lib.readpng_read.restype = ctypes.c_int
    lib.readpng_free.argtypes = [ctypes.POINTER(_Result)]
    lib.readpng_free.restype = None
    _LIB = lib
    return lib


def _is_raw(source) -> bool:
    return isinstance(source, (bytes, bytearray, memoryview))


def _condition(value) -> bool:
    """R's if() on the info argument."""

    if isinstance(value, (list, tuple)):
        if len(value) > 1:
            raise PNGError("the condition has length > 1")
        if len(value) == 0:
            raise PNGError("argument is of length zero")
        value = value[0]
    if value is None:
        raise PNGError("argument is of length zero")
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        if value in _TRUE:
            return True
        if value in _FALSE:
            return False
        raise PNGError("argument is not interpretable as logical")
    if isinstance(value, int):
        if value == _NA_INT:
            raise PNGError("argument is not interpretable as logical")
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            raise PNGError("argument is not interpretable as logical")
        return value != 0.0
    raise PNGError("argument is not interpretable as logical")


def _as_integer(value) -> int:
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return _NA_INT
        value = value[0]
    if value is None:
        return _NA_INT
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        if value == _NA_INT:
            return _NA_INT
        if value < -2147483647 or value > 2147483647:
            warnings.warn(
                "NAs introduced by coercion to integer range",
                RuntimeWarning,
                stacklevel=3,
            )
            return _NA_INT
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return _NA_INT
        if math.isinf(value) or value <= -2147483648.0 or value >= 2147483648.0:
            warnings.warn(
                "NAs introduced by coercion to integer range",
                RuntimeWarning,
                stacklevel=3,
            )
            return _NA_INT
        return int(math.trunc(value))
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=3)
            return _NA_INT
        return _as_integer(number)
    warnings.warn("NAs introduced by coercion", RuntimeWarning, stacklevel=3)
    return _NA_INT


def _path_expand_first(source) -> str:
    if isinstance(source, os.PathLike):
        source = os.fspath(source)
    if isinstance(source, str):
        paths = [source]
    elif isinstance(source, (list, tuple)):
        if len(source) == 0:
            raise PNGError("invalid filename")
        if not all(isinstance(item, str) for item in source):
            raise PNGError("invalid 'path' argument")
        paths = list(source)
    else:
        raise PNGError("invalid 'path' argument")
    return os.path.expanduser(paths[0])


def _text_of(result: _Result) -> NamedCharacter | None:
    if result.ntext <= 0:
        return None
    pairs = []
    for i in range(result.ntext):
        if result.text_key_na[i]:
            name = None
        else:
            raw = result.text_keys[i]
            name = None if raw is None else raw.decode("utf-8", "surrogateescape")
        if result.text_val_na[i]:
            value = None
        else:
            raw = result.text_vals[i]
            value = None if raw is None else raw.decode("utf-8", "surrogateescape")
        pairs.append((name, value))
    return NamedCharacter(pairs)


def _take_metadata(info: dict):
    text = info.get("text")
    if text is None or "R.metadata" not in text.names:
        return None
    raw_text = None
    for name, value in text.pairs:
        if name == "R.metadata":
            raw_text = value
            break
    if raw_text is None:
        raise PNGError("invalid argument")
    try:
        metadata = unserialize(raw_text.encode("utf-8", "surrogateescape"))
    except ValueError as error:
        raise PNGError(str(error)) from error
    kept = [(name, value) for name, value in text.pairs if name != "R.metadata"]
    info["text"] = NamedCharacter(kept)
    return metadata


def _warn(result: _Result) -> None:
    if not result.warning:
        return
    text = bytes(result.warning).split(b"\0", 1)[0].decode("utf-8", "surrogateescape")
    for line in text.split("\n"):
        if line:
            warnings.warn(line, RuntimeWarning, stacklevel=3)


def readPNG(source, native=False, info=False):
    """Read a PNG file or raw vector into an array, or a native raster.

    ``native=False`` returns reals in ``[0, 1]`` with shape height, width,
    and channels when there is more than one channel. ``native=True`` returns
    the integer vector R stores for ``nativeRaster``, one row of pixels after
    another, shaped ``(height, width)``. ``info=True`` attaches the tag list
    and, when the file has ``R.metadata``, the unserialized object.
    """

    want_info = _condition(info)
    if _is_raw(source):
        raw = bytes(source)
        path = None
    else:
        path = _path_expand_first(source)
        raw = None
    native_flag = _as_integer(native) != 0
    lib = _library()
    result = _Result()
    if raw is None:
        code = lib.readpng_read(
            os.fsencode(path),
            None,
            0,
            int(native_flag),
            int(want_info),
            ctypes.byref(result),
        )
    else:
        if raw:
            buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
            code = lib.readpng_read(
                None,
                buffer,
                len(raw),
                int(native_flag),
                int(want_info),
                ctypes.byref(result),
            )
        else:
            code = lib.readpng_read(
                None,
                None,
                0,
                int(native_flag),
                int(want_info),
                ctypes.byref(result),
            )
    try:
        if not code or not result.ok:
            message = bytes(result.error).split(b"\0", 1)[0].decode("utf-8", "surrogateescape")
            raise PNGError(message or "libpng error: ")
        _warn(result)
        if native_flag:
            count = result.n_samples
            if count:
                flat = np.ctypeslib.as_array(result.native_pixels, shape=(count,)).copy()
            else:
                flat = np.zeros(0, dtype=np.int32)
            image = flat.reshape((result.height, result.width), order="C")
            channels = int(result.channels)
        else:
            count = result.n_samples
            if count:
                flat = np.ctypeslib.as_array(result.samples, shape=(count,)).copy()
            else:
                flat = np.zeros(0, dtype=np.float64)
            if result.planes > 1:
                image = flat.reshape((result.height, result.width, result.planes), order="F")
            else:
                image = flat.reshape((result.height, result.width), order="F")
            channels = None
        attached = None
        metadata = None
        if result.has_info:
            attached = {
                "dim": (int(result.info_width), int(result.info_height)),
                "bit.depth": int(result.info_bit_depth),
            }
            if result.color_is_int:
                attached["color.type"] = int(result.color_int)
            else:
                attached["color.type"] = bytes(result.color_type).split(b"\0", 1)[0].decode("ascii")
            if result.has_gamma:
                attached["gamma"] = float(result.gamma)
            if result.has_dpi:
                attached["dpi"] = (float(result.dpi_x), float(result.dpi_y))
            if result.has_asp:
                attached["asp"] = float(result.asp)
            text = _text_of(result)
            if text is not None:
                attached["text"] = text
                metadata = _take_metadata(attached)
        return PNGImage(image, info=attached, metadata=metadata, channels=channels)
    finally:
        lib.readpng_free(ctypes.byref(result))
