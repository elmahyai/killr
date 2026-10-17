"""Write a PNG the way the R package png 0.1-9 writes one.

Pixels go to the system libpng through a small C wrapper. libpng longjmps
on error, so that jump stays in the wrapper and ctypes only sees the result.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from pathlib import Path

import numpy as np

from png.readPNG import NamedCharacter, PNGError, PNGImage, _path_expand_first

_LIB = None


class _WriteResult(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ("length", ctypes.c_size_t),
        ("ok", ctypes.c_int),
        ("error", ctypes.c_char * 1024),
        ("warning", ctypes.c_char * 2048),
        ("warning_used", ctypes.c_size_t),
    ]


def _library():
    global _LIB
    if _LIB is not None:
        return _LIB
    here = Path(__file__).resolve().parent
    source = here / "_writepng.c"
    binary = here / "_writepng.so"
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        subprocess.check_call(
            ["gcc", "-shared", "-fPIC", "-O2", "-o", str(binary), str(source), "-lpng"],
        )
    lib = ctypes.CDLL(str(binary))
    lib.writepng_write.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.c_int,
        ctypes.POINTER(_WriteResult),
    ]
    lib.writepng_write.restype = ctypes.c_int
    lib.writepng_free.argtypes = [ctypes.POINTER(_WriteResult)]
    lib.writepng_free.restype = None
    _LIB = lib
    return lib


def _default_text(image):
    info = getattr(image, "info", None)
    if info is None:
        return None
    return info.get("text")


def _default_metadata(image):
    return getattr(image, "metadata", None)


def _serialize_metadata(metadata) -> str:
    packages = Path(__file__).resolve().parents[2]
    digest_root = packages / "digest"
    import sys

    if str(digest_root) not in sys.path:
        sys.path.insert(0, str(digest_root))
    from digest.serialize import serialize

    return serialize(metadata, version=2, ascii=True).decode("latin1")


def _prepare_text(text, metadata):
    if text is not None and not isinstance(text, NamedCharacter):
        if isinstance(text, dict):
            pairs = list(text.items())
        elif isinstance(text, (list, tuple)):
            pairs = [(None, str(item)) for item in text]
        else:
            pairs = [(None, str(text))]
        text = NamedCharacter(pairs)
    if metadata is not None:
        rmd = _serialize_metadata(metadata)
        chunk = NamedCharacter([("R.metadata", rmd)])
        if text is None:
            text = chunk
        else:
            text = NamedCharacter(list(text.pairs) + list(chunk.pairs))
    if text is None:
        return [], [], 0
    keys = []
    vals = []
    for name, value in text.pairs:
        keys.append("" if name is None else str(name))
        vals.append("" if value is None else str(value))
    return keys, vals, len(keys)


def _parse_dpi(dpi):
    if dpi is None:
        return 0.0, 0.0, 0
    if isinstance(dpi, (list, tuple, np.ndarray)):
        if len(dpi) < 1 or len(dpi) > 2:
            raise PNGError("invalid dpi specification - must be NULL or a numeric vector of length 1 or 2")
        dpi_x = float(dpi[0])
        dpi_y = float(dpi[1]) if len(dpi) > 1 else dpi_x
        return dpi_x, dpi_y, 1
    if isinstance(dpi, (int, float, np.integer, np.floating)):
        value = float(dpi)
        return value, value, 1
    raise PNGError("invalid `dpi' specification - must be NULL or a numeric vector of length 1 or 2")


def _parse_asp(asp):
    if asp is None:
        return 0.0, 0.0, 0
    if isinstance(asp, (list, tuple, np.ndarray)):
        if len(asp) != 1:
            raise PNGError("invalid `asp' specification - must be NULL or a numeric scalar")
        asp = asp[0]
    if not isinstance(asp, (int, float, np.integer, np.floating)):
        raise PNGError("invalid `asp' specification - must be NULL or a numeric scalar")
    return float(asp), 1.0, 2


def _image_layout(image):
    native = False
    raw_array = False
    channels_attr = -1
    arr = np.asarray(image)
    if isinstance(image, PNGImage) and image.channels is not None:
        native = True
        channels_attr = int(image.channels)
        if arr.dtype != np.int32:
            arr = arr.astype(np.int32, copy=False)
    elif arr.dtype == np.uint8 and arr.ndim == 3 and arr.shape[0] == 4:
        raw_array = True
        planes, width, height = (int(arr.shape[0]), int(arr.shape[1]), int(arr.shape[2]))
        return native, raw_array, height, width, planes, channels_attr, arr
    elif arr.dtype in (np.float32, np.float64, np.int32) and arr.ndim in (2, 3):
        if arr.dtype == np.int32 and arr.ndim == 2:
            native = True
            if isinstance(image, PNGImage) and image.channels is not None:
                channels_attr = int(image.channels)
            else:
                channels_attr = 4
        elif arr.dtype != np.float64 and not native:
            arr = arr.astype(np.float64, copy=False)
    else:
        raise PNGError("image must be a matrix or array of raw or real numbers")

    if arr.ndim == 2:
        height, width = int(arr.shape[0]), int(arr.shape[1])
        planes = 1
    elif arr.ndim == 3:
        height, width, planes = int(arr.shape[0]), int(arr.shape[1]), int(arr.shape[2])
    else:
        raise PNGError("image must be a matrix or an array of two or three dimensions")

    if planes < 1 or planes > 4:
        raise PNGError("image must have either 1 (grayscale), 2 (GA), 3 (RGB) or 4 (RGBA) planes")
    if native and planes > 1 and not raw_array:
        raise PNGError("native raster must be a matrix")
    return native, raw_array, height, width, planes, channels_attr, arr


def _call_write(
    arr,
    native,
    raw_array,
    height,
    width,
    planes,
    channels_attr,
    path,
    to_raw,
    dpi_x,
    dpi_y,
    use_dpi,
    keys,
    vals,
    ntext,
):
    lib = _library()
    result = _WriteResult()
    real_ptr = None
    native_ptr = None
    raw_ptr = None
    if not native and not raw_array:
        data = np.asfortranarray(arr, dtype=np.float64)
        real_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    elif raw_array:
        view = np.ascontiguousarray(arr.view(np.int32))
        raw_ptr = view.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
    else:
        data = np.ascontiguousarray(arr, dtype=np.int32)
        native_ptr = data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

    key_array = (ctypes.c_char_p * ntext)(*(k.encode("utf-8") for k in keys)) if ntext else None
    val_array = (ctypes.c_char_p * ntext)(*(v.encode("utf-8") for v in vals)) if ntext else None
    path_bytes = None if path is None else os.fsencode(path)

    try:
        code = lib.writepng_write(
            real_ptr,
            native_ptr,
            raw_ptr,
            int(native),
            int(raw_array),
            height,
            width,
            planes,
            channels_attr,
            path_bytes,
            int(to_raw),
            dpi_x,
            dpi_y,
            use_dpi,
            key_array,
            val_array,
            ntext,
            ctypes.byref(result),
        )
        if not code or not result.ok:
            message = bytes(result.error).split(b"\0", 1)[0].decode("utf-8", "surrogateescape")
            raise PNGError(message or "libpng error: ")
        if to_raw:
            length = int(result.length)
            if length:
                return bytes(ctypes.string_at(result.data, length))
            return b""
        return None
    finally:
        lib.writepng_free(ctypes.byref(result))


def writePNG(image, target=None, dpi=None, asp=None, text=None, metadata=None):
    """Write an array or native raster to PNG bytes, a path, or a binary stream.

    ``target`` defaults to returning a ``bytes`` object, like R's ``raw()``.
    A path string or path-like object writes a file and returns ``None``.
    A binary stream receives the PNG bytes and returns ``None``.
    """

    if text is None:
        text = _default_text(image)
    if metadata is None:
        metadata = _default_metadata(image)

    dpi_x, dpi_y, use_dpi = _parse_dpi(dpi)
    asp_x, asp_y, asp_mode = _parse_asp(asp)
    if use_dpi and asp_mode:
        raise PNGError("`asp' and `dpi' are mutually exclusive")
    if asp_mode:
        dpi_x, dpi_y, use_dpi = asp_x, asp_y, asp_mode

    native, raw_array, height, width, planes, channels_attr, arr = _image_layout(image)
    keys, vals, ntext = _prepare_text(text, metadata)

    if target is None or isinstance(target, (bytes, bytearray, memoryview)):
        return _call_write(
            arr,
            native,
            raw_array,
            height,
            width,
            planes,
            channels_attr,
            None,
            True,
            dpi_x,
            dpi_y,
            use_dpi,
            keys,
            vals,
            ntext,
        )

    if isinstance(target, (str, os.PathLike)):
        path = _path_expand_first(target)
        _call_write(
            arr,
            native,
            raw_array,
            height,
            width,
            planes,
            channels_attr,
            path,
            False,
            dpi_x,
            dpi_y,
            use_dpi,
            keys,
            vals,
            ntext,
        )
        return None

    if hasattr(target, "write"):
        payload = _call_write(
            arr,
            native,
            raw_array,
            height,
            width,
            planes,
            channels_attr,
            None,
            True,
            dpi_x,
            dpi_y,
            use_dpi,
            keys,
            vals,
            ntext,
        )
        target.write(payload)
        return None

    raise PNGError("invalid filename")
