"""ifft, fftshift, and ifftshift from fft.R."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError


def _fft_vector(x, message: str) -> np.ndarray:
    if isinstance(x, (str, bytes)):
        raise PracmaError(message)
    array = np.asarray(x)
    if array.ndim != 1 and not (array.ndim == 0):
        raise PracmaError(message)
    array = array.reshape(-1)
    if array.dtype == bool or array.dtype == object or not (
        np.issubdtype(array.dtype, np.number)
    ):
        raise PracmaError(message)
    return array


def ifft(x):
    if x is None or np.asarray(x).size == 0:
        return np.array([])
    values = _fft_vector(x, "Argument 'x' must be real or complex vector.")
    # NumPy's inverse already divides by n, which is what pracma does after
    # R's unnormalized fft(inverse=TRUE).
    return np.fft.ifft(values.astype(complex))


def fftshift(x):
    values = _fft_vector(x, "Argument 'x' must be a real or complex vector.")
    count = values.size
    half = math.ceil(count / 2)
    return np.concatenate([values[half:], values[:half]])


def ifftshift(x):
    values = _fft_vector(x, "Argument 'x' must be a real or complex vector.")
    count = values.size
    half = math.floor(count / 2)
    return np.concatenate([values[half:], values[:half]])
