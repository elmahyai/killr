"""Arithmetic that R's graphics engine applies, for the default pdf device.

R's default device here is the 7 x 7 inch pdf device with the default
margins mai = c(1.02, 0.82, 0.82, 0.42) and pointsize 12. The plot region is
therefore 5.76 x 5.16 inches. Helpers take the region size as ``pin`` so a
caller with another axes box gets the same R arithmetic.
"""

import math

import numpy as np
from matplotlib.colors import to_rgb

PDF_PIN = (5.76, 5.16)
POINTSIZE = 12.0
# Ascent of "M" in Helvetica (bounding box top). R uses it for strheight().
HELVETICA_M_ASCENT = 718
# Helvetica character widths (1/1000 em) for ASCII 32..126, read from the
# grDevices Helvetica.afm file that R's pdf device uses.
_HELVETICA_WX_TEXT = (
    "32:278,33:278,34:355,35:556,36:556,37:889,38:667,39:222,40:333,41:333,"
    "42:389,43:584,44:278,45:333,46:278,47:278,48:556,49:556,50:556,51:556,"
    "52:556,53:556,54:556,55:556,56:556,57:556,58:278,59:278,60:584,61:584,"
    "62:584,63:556,64:1015,65:667,66:667,67:722,68:722,69:667,70:611,71:778,"
    "72:722,73:278,74:500,75:667,76:556,77:833,78:722,79:778,80:667,81:778,"
    "82:722,83:667,84:611,85:722,86:667,87:944,88:667,89:667,90:611,91:278,"
    "92:278,93:278,94:469,95:556,96:222,97:556,98:556,99:500,100:556,101:556,"
    "102:278,103:556,104:556,105:222,106:222,107:500,108:222,109:833,110:556,"
    "111:556,112:556,113:556,114:333,115:500,116:278,117:556,118:500,119:722,"
    "120:500,121:500,122:500,123:334,124:260,125:334,126:584"
)
HELVETICA_WX = {
    int(k): int(v) for k, v in (item.split(":") for item in _HELVETICA_WX_TEXT.split(","))
}


def r_extend(lo, hi, frac=0.04):
    """Axis limits with R's default 4 percent extension (xaxs = "r")."""
    d = hi - lo
    return lo - frac * d, hi + frac * d


def r_range_finite(values):
    """range(values, finite = TRUE) as a (min, max) tuple."""
    v = np.asarray(values, dtype=float).ravel()
    v = v[np.isfinite(v)]
    return float(v.min()), float(v.max())


def r_plot_limits(xvals, yvals, pin):
    """xlim and ylim that plot(x, y, asp = 1) gives on a region of size pin."""
    xlim = r_extend(*r_range_finite(xvals))
    ylim = r_extend(*r_range_finite(yvals))
    return r_asp_equal(xlim, ylim, pin)


def r_asp_equal(xlim, ylim, pin):
    """Expand both limits so one unit is the same length on both axes."""
    xdelta = xlim[1] - xlim[0]
    ydelta = ylim[1] - ylim[0]
    scale = max(xdelta / pin[0], ydelta / pin[1])
    xc = 0.5 * (xlim[0] + xlim[1])
    yc = 0.5 * (ylim[0] + ylim[1])
    return (
        (xc - 0.5 * scale * pin[0], xc + 0.5 * scale * pin[0]),
        (yc - 0.5 * scale * pin[1], yc + 0.5 * scale * pin[1]),
    )


def _char_wx(ch):
    code = ord(ch)
    if code not in HELVETICA_WX:
        raise ValueError(f"no Helvetica metric for character {ch!r}")
    return HELVETICA_WX[code]


def r_strwidth(names, cex, xlim, pin_x):
    """strwidth(names, cex) in user coordinates on the pdf device."""
    unit = (xlim[1] - xlim[0]) / pin_x
    size_in = POINTSIZE * cex / 72.0
    return np.array([
        np.nan if s is None else sum(_char_wx(ch) for ch in str(s)) / 1000.0 * size_in * unit
        for s in names
    ])


def r_strheight(cex, ylim, pin_y):
    """strheight(names, cex) in user coordinates (same for every string)."""
    unit = (ylim[1] - ylim[0]) / pin_y
    return HELVETICA_M_ASCENT / 1000.0 * (POINTSIZE * cex / 72.0) * unit


def col2rgb(name):
    """col2rgb for a colour name or hex string, as integers 0..255."""
    return [int(round(c * 255)) for c in to_rgb(name)]


def rgb_hex(r, g, b):
    """rgb(r, g, b, maxColorValue = 255): values are truncated to integers."""
    def conv(v):
        return min(255, max(0, int(math.trunc(float(v)))))
    return "#%02X%02X%02X" % (conv(r), conv(g), conv(b))


def r_seq(start, stop, n):
    """seq(start, stop, length = n)."""
    return np.linspace(start, stop, n)


def contrib_palette(base, n_rows, mode, cst=230.0, nc0=50):
    """Colour look-up table that plot.ca and plot.mjca build for contributions.

    ``mode`` is "relative" or "absolute". Returns the nc0 colours as hex strings.
    """
    cb = col2rgb(base)
    if mode == "relative":
        cols = [
            rgb_hex(*(r_seq(cst, cb[k], nc0)[i] for k in range(3)))
            for i in range(nc0)
        ]
        return cols
    # absolute: a half ramp from white-ish to a midpoint, then to the base colour
    p = [cb[k] + (cst - cb[k]) / n_rows for k in range(3)]
    half = nc0 // 2
    first = [rgb_hex(*(r_seq(cst, p[k], half)[i] for k in range(3))) for i in range(half)]
    second = [rgb_hex(*(r_seq(p[k], cb[k], half)[i] for k in range(3))) for i in range(half)]
    return first + second


def r_index_colours(lut, index_values):
    """lut[index] with R's indexing rules: fractions truncate, 0 drops, > length is NA."""
    out = []
    for v in np.asarray(index_values, dtype=float):
        if not np.isfinite(v):
            out.append(None)
            continue
        i = int(math.trunc(v))
        if i == 0:
            continue
        out.append(lut[i - 1] if 1 <= i <= len(lut) else None)
    return out


def r_rep_times(values, times):
    """rep(values, times) for a vector of times."""
    values = list(values)
    times = list(times)
    if len(times) == 1:
        return values * int(times[0])
    if len(times) != len(values):
        raise ValueError("invalid 'times' argument")
    out = []
    for v, t in zip(values, times):
        out.extend([v] * int(t))
    return out


def r_round(x, digits=1):
    """round(x, digits) as R prints the value inside paste0()."""
    return float(np.round(x, digits))


def r_num_text(x):
    """as.character() for a number rounded to 15 significant digits."""
    s = "%.15g" % x
    return s
