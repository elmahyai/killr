"""Draw R plotting symbols (pch), text labels and lines with Matplotlib.

The data a plot function computes is kept as plain lists and arrays. These
helpers only turn that data into Matplotlib artists, so the computation can be
timed and checked without drawing.

R's pch codes are mapped to the nearest Matplotlib marker. ``None`` means the
code draws nothing (R leaves 26:31 unused and ignores codes outside the
printable ranges). Codes 32:126 and 160:254 are glyphs in R; they are drawn as
the character itself.
"""

import numpy as np
from matplotlib.colors import to_rgba

# pch code -> (Matplotlib marker, filled)
_PCH_MARKER = {
    0: ("s", False), 1: ("o", False), 2: ("^", False), 3: ("+", None),
    4: ("x", None), 5: ("D", False), 6: ("v", False), 7: ("s", False),
    8: ("*", None), 9: ("D", False), 10: ("o", False), 11: ("*", None),
    12: ("s", False), 13: ("o", False), 14: ("s", False), 15: ("s", True),
    16: ("o", True), 17: ("^", True), 18: ("D", True), 19: ("o", True),
    20: ("o", True), 21: ("o", False), 22: ("s", False), 23: ("D", False),
    24: ("^", False), 25: ("v", False),
}
_GLYPH_RANGES = ((32, 126), (160, 254))


def pch_kind(code):
    """Return ("marker", marker, filled), ("glyph", char) or ("none",)."""
    code = int(code)
    if code in _PCH_MARKER:
        marker, filled = _PCH_MARKER[code]
        return ("marker", marker, filled)
    for lo, hi in _GLYPH_RANGES:
        if lo <= code <= hi:
            return ("glyph", chr(code))
    return ("none",)


def _colour_at(col, i):
    if col is None or len(col) == 0:
        return None
    c = col[i % len(col)]
    return c


_LINE_MARKERS = ("+", "x", "|", "_")


def draw_points(ax, x, y, pch, cex, col, size=6.0):
    """points(x, y, pch, cex, col) for raw R-style vectors (recycled like R)."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    artists = []
    groups = {}
    for i in range(len(x)):
        if not (np.isfinite(x[i]) and np.isfinite(y[i])):
            continue
        colour = _colour_at(col, i)
        if colour is None:
            continue
        code = _colour_at(pch, i)
        if code is None or not np.isfinite(float(code)):
            continue
        kind = pch_kind(code)
        if kind[0] == "none":
            continue
        scale = float(_colour_at(cex, i) or 1.0)
        if kind[0] == "glyph":
            artists.append(ax.text(x[i], y[i], kind[1], ha="center", va="center",
                                   color=to_rgba(colour), fontsize=size * scale * 2))
            continue
        key = (kind[1], kind[2], scale, colour)
        groups.setdefault(key, []).append((x[i], y[i]))
    for (marker, filled, scale, colour), pts in groups.items():
        pts = np.asarray(pts)
        s = (size * scale) ** 2
        # line-only markers (+, x) have no face, so Matplotlib takes their colour
        # from color=; hollow markers keep an empty face
        if filled or marker in _LINE_MARKERS:
            artists.append(ax.scatter(pts[:, 0], pts[:, 1], marker=marker, s=s,
                                      color=colour))
        else:
            artists.append(ax.scatter(pts[:, 0], pts[:, 1], marker=marker, s=s,
                                      facecolors="none", edgecolors=colour))
    return artists


def draw_text(ax, x, y, labels, col, fontsize=9.0):
    """text(x, y, labels, col) with R's default centred adjustment."""
    artists = []
    for i, label in enumerate(labels):
        if label is None or not (np.isfinite(x[i]) and np.isfinite(y[i])):
            continue
        colour = _colour_at(col, i)
        artists.append(ax.text(x[i], y[i], str(label), ha="center", va="center",
                               color=to_rgba(colour) if colour else None,
                               fontsize=fontsize))
    return artists


def draw_lines(ax, x, y, col, lwd=1.0):
    """lines(x, y, col, lwd) for one polyline."""
    colour = col[0] if col else None
    return [ax.plot(x, y, color=colour, linewidth=lwd)[0]]
