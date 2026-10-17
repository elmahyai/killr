"""Short-time Fourier transform (e1071::stft)."""

from __future__ import annotations

import numpy as np

from e1071.windows import hamming_window, hanning_window, rectangle_window

_WTYPE = {
    "hanning.window": hanning_window,
    "hamming.window": hamming_window,
    "rectangle.window": rectangle_window,
}


def _window_coef(wtype: str, win: int):
    func = _WTYPE.get(wtype)
    if func is None:
        raise ValueError(f"unknown window type {wtype!r}")
    return np.asarray(func(win), dtype=float)


def stft(X, win=None, inc=None, coef=64, wtype="hanning.window"):
    x = np.asarray(X, dtype=float).ravel()
    n = x.size
    if win is None:
        win = min(80, n // 10)
    if inc is None:
        inc = min(24, n // 30)

    numcoef = 2 * coef
    if win > numcoef:
        win = numcoef
        print(f"stft: window size adjusted to {win} .")

    numwin = int((n - win) / inc)
    wincoef = _window_coef(wtype, win)

    z = np.zeros((numwin + 1, numcoef), dtype=float)
    y = np.zeros((numwin + 1, numcoef), dtype=complex)
    st = 0
    for i in range(numwin + 1):
        z[i, :win] = x[st : st + win] * wincoef
        y[i, :] = np.fft.fft(z[i, :])
        st += inc

    values = np.abs(y[:, :coef])
    return {
        "values": values,
        "windowsize": win,
        "increment": inc,
        "windowtype": wtype,
    }
