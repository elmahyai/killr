"""Peak finding with a sign-run pattern."""

from __future__ import annotations

import re
import warnings

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector


def findpeaks(x, nups=1, ndowns=None, zero="0", peakpat=None, minpeakheight=-np.inf,
              minpeakdistance=1, threshold=0, npeaks=0, sortstr=False):
    if ndowns is None:
        ndowns = nups
    if not (is_r_vector(x) and is_r_numeric(x)) and not (np.asarray(x).size == 0):
        raise PracmaError('is.vector(x, mode = "numeric") || length(is.na(x)) == 0 is not TRUE')
    if zero not in ("0", "+", "-"):
        raise PracmaError("Argument 'zero' can only be '0', '+', or '-'.")
    series = np.asarray(x, dtype=float).reshape(-1)
    signs = np.sign(np.diff(series))
    text = "".join(str(int(value)) for value in signs)
    text = text.replace("-1", "-").replace("1", "+")
    if zero != "0":
        text = text.replace("0", zero)
    if peakpat is None:
        peakpat = f"[+]{{{int(nups)},}}[-]{{{int(ndowns)},}}"
    matches = list(re.finditer(peakpat, text))
    if not matches:
        return None
    x1 = np.array([match.start() + 1 for match in matches], dtype=float)
    x2 = x1 + np.array([match.end() - match.start() for match in matches], dtype=float)
    count = x1.size
    xp = np.zeros(count)
    xv = np.zeros(count)
    for i in range(count):
        start = int(x1[i])
        stop = int(x2[i])
        window = series[start - 1:stop]
        xp[i] = float(np.argmax(window) + start)
        xv[i] = series[int(xp[i]) - 1]
    left = series[x1.astype(int) - 1]
    right = series[x2.astype(int) - 1]
    keep = (xv >= minpeakheight) & (xv - np.maximum(left, right) >= threshold)
    peaks = np.column_stack([xv[keep], xp[keep], x1[keep], x2[keep]])
    if minpeakdistance < 1:
        warnings.warn("Handling 'minpeakdistance < 1' is logically not possible.", stacklevel=2)
    if sortstr or minpeakdistance > 1:
        order = np.argsort(-peaks[:, 0], kind="stable")
        peaks = peaks[order]
    if peaks.size == 0:
        return None
    if minpeakdistance > 1:
        bad = np.zeros(peaks.shape[0], dtype=bool)
        for i in range(peaks.shape[0]):
            if not bad[i]:
                distance = np.abs(peaks[i, 1] - peaks[:, 1])
                bad = bad | ((distance > 0) & (distance < minpeakdistance))
        peaks = peaks[~bad]
    if npeaks > 0 and npeaks < peaks.shape[0]:
        peaks = peaks[:int(npeaks)]
    return peaks
