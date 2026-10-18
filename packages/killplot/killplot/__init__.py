"""Chart functions that Matplotlib does not already provide.

If a chart can be drawn in one to three lines of Matplotlib, call Matplotlib.
Add a function here only when Matplotlib has no such function.
"""

import math

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath


def fan(ax, observed, lower, upper, colors):
    """Fill a forecast fan. ``lower`` and ``upper`` include the last observation.

    Each row of ``lower`` and ``upper`` is one interval, from the narrowest
    band to the widest. ``colors`` is one grey level per interval.
    """
    n_obs = observed.shape[0]
    n_ahead = lower.shape[1] - 1
    axis_x = np.arange(n_obs - 1, n_obs + n_ahead)
    ax.plot(np.arange(n_obs), observed, color="black")
    for level in range(lower.shape[0]):
        ax.fill(
            np.concatenate([axis_x, axis_x[::-1]]),
            np.concatenate([lower[level], upper[level][::-1]]),
            color=str(colors[level]),
            linewidth=0,
        )


# ---------------------------------------------------------------------------
# statefig: a state-transition diagram (survival::statefig).
#
# R draws on the base graphics device. The layout, the arc geometry and the
# returned box centres are computed exactly as in R; the drawing uses
# Matplotlib on ``ax``. Text widths come from the font metrics of Matplotlib,
# so the arrow ends differ from R's device by font metrics only.
# ---------------------------------------------------------------------------

_PI_LOCAL = 3.1415926545898  # statefig.R sets this constant inside statefigx/y
_R_PALETTE = ["white", "#DF536B", "#61D04F", "#2297E6", "#28E2E5", "#CD0BBC", "#F5C710", "gray62"]
_R_LTY = {1: "-", 2: "--", 3: ":", 4: "-.", 5: "--", 6: "-."}


def _rep_length(values, n):
    """R's ``rep(values, length = n)``."""
    vals = list(values) if isinstance(values, (list, tuple, np.ndarray)) else [values]
    return [vals[i % len(vals)] for i in range(n)]


def _r_color(value):
    if isinstance(value, (int, float, np.integer, np.floating)):
        idx = int(value)
        return _R_PALETTE[idx % len(_R_PALETTE)] if idx > 0 else "white"
    return value


def _r_linestyle(value):
    if isinstance(value, (int, float, np.integer, np.floating)):
        return _R_LTY.get(int(value), "-")
    return value


def _rmin(*arrays):
    """``min(..., na.rm = TRUE)`` over vectors that may be None; Inf if empty."""
    parts = [np.asarray(a, dtype=float).reshape(-1) for a in arrays if a is not None]
    parts = [p for p in parts if p.size]
    if not parts:
        return math.inf
    return float(np.min(np.concatenate(parts)))


def _rmax(*arrays):
    """``max(..., na.rm = TRUE)`` over vectors that may be None; -Inf if empty."""
    parts = [np.asarray(a, dtype=float).reshape(-1) for a in arrays if a is not None]
    parts = [p for p in parts if p.size]
    if not parts:
        return -math.inf
    return float(np.max(np.concatenate(parts)))


def _statefigx(x, C, r, a1, a2):
    temp = (x - C[0]) / r
    if abs(temp) > 1:
        return None
    phi = math.acos(temp)
    pi = _PI_LOCAL
    if x > C[0]:
        phi = np.array([phi, pi - phi])
    else:
        phi = -np.array([phi, pi - phi])
    phi = np.concatenate([phi, -phi, 2 * pi - phi])
    amax = max(a1, a2)
    amin = min(a1, a2)
    return phi[(phi < amax) & (phi > amin)]


def _statefigy(y, C, r, a1, a2):
    pi = _PI_LOCAL
    amax = max(a1, a2)
    amin = min(a1, a2)
    temp = (y - C[1]) / r
    if abs(temp) > 1:
        return None
    phi = math.asin(temp)
    phi = np.array([phi, np.sign(phi) * pi - phi])
    phi = np.concatenate([phi, phi + 2 * pi])
    return phi[(phi < amax) & (phi > amin)]


def _phi(x1, y1, x2, y2, d, delta1, delta2):
    """Arc through two box centres at height ``d`` (statefig.R ``phi``)."""
    theta = math.atan2(y2 - y1, x2 - x1)
    if abs(d) < 0.001:
        d = 0.001
    z = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 2
    ab = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
    r = abs(z * (1 + d * d) / (2 * d))
    if d > 0:
        C = ab + (r - d * z) * np.array([-math.sin(theta), math.cos(theta)])
    else:
        C = ab + (r + d * z) * np.array([math.sin(theta), -math.cos(theta)])
    a1 = math.atan2(y1 - C[1], x1 - C[0])
    a2 = math.atan2(y2 - C[1], x2 - C[0])
    if abs(a2 - a1) > math.pi:
        if a1 > 0:
            a2 = a2 + 2 * math.pi
        else:
            a1 = a1 + 2 * math.pi
    if d > 0:
        phi1 = _rmin(
            _statefigx(x1 + delta1[0], C, r, a1, a2),
            _statefigx(x1 - delta1[0], C, r, a1, a2),
            _statefigy(y1 + delta1[1], C, r, a1, a2),
            _statefigy(y1 - delta1[1], C, r, a1, a2),
        )
        phi2 = _rmax(
            _statefigx(x2 + delta2[0], C, r, a1, a2),
            _statefigx(x2 - delta2[0], C, r, a1, a2),
            _statefigy(y2 + delta2[1], C, r, a1, a2),
            _statefigy(y2 - delta2[1], C, r, a1, a2),
        )
    else:
        phi1 = _rmax(
            _statefigx(x1 + delta1[0], C, r, a1, a2),
            _statefigx(x1 - delta1[0], C, r, a1, a2),
            _statefigy(y1 + delta1[1], C, r, a1, a2),
            _statefigy(y1 - delta1[1], C, r, a1, a2),
        )
        phi2 = _rmin(
            _statefigx(x2 + delta2[0], C, r, a1, a2),
            _statefigx(x2 - delta2[0], C, r, a1, a2),
            _statefigy(y2 + delta2[1], C, r, a1, a2),
            _statefigy(y2 - delta2[1], C, r, a1, a2),
        )
    return {"center": C, "angle": np.array([phi1, phi2]), "r": r}


def _text_extent(text, cex):
    """Width and height of ``text`` in inches, from Matplotlib font metrics."""
    prop = FontProperties(size=10 * cex)
    width_pt, height_pt, _ = TextToPath().get_text_width_height_descent(text, prop, ismath=False)
    return width_pt / 72.0, height_pt / 72.0


def statefig(
    ax,
    layout,
    connect,
    statenames,
    margin=0.03,
    box=True,
    cex=1.0,
    col=1,
    lwd=1,
    lty=1,
    bcol=None,
    acol=None,
    alwd=None,
    alty=None,
    offset=0.0,
):
    """Draw a state diagram on ``ax`` and return the box centres.

    ``connect`` is a square matrix; ``connect[i, j] != 0`` draws an arrow from
    state ``i`` to state ``j``. ``statenames`` gives the state labels in row
    order. ``layout`` is a vector of boxes per column (left to right), a
    one-column matrix (top to bottom), or an ``n x 2`` matrix of centres in
    ``[0, 1]``. The return value is the ``n x 2`` array of box centres, one row
    per state, as R's ``statefig`` returns invisibly.
    """
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    layout = np.asarray(layout)
    connect = np.asarray(connect, dtype=float)
    if connect.ndim != 2 or connect.shape[0] != connect.shape[1]:
        raise ValueError("connect must be a square matrix")
    nstate = connect.shape[0]
    statenames = [str(s) for s in statenames]
    if len(statenames) != nstate:
        raise ValueError("statenames must have one entry per state")
    if not np.issubdtype(layout.dtype, np.number):
        raise ValueError("layout must be a numeric vector or matrix")

    if bcol is None:
        bcol = col
    if acol is None:
        acol = col
    if alwd is None:
        alwd = lwd
    if alty is None:
        alty = lty

    narrow = int(np.sum(connect != 0))
    acol = _rep_length(acol, narrow)
    alwd = _rep_length(alwd, narrow)
    alty = _rep_length(alty, narrow)
    bcol = _rep_length(bcol, nstate)
    lty = _rep_length(lty, nstate)
    lwd = _rep_length(lwd, nstate)
    col = _rep_length(col, nstate)

    if layout.ndim == 2 and layout.shape[1] == 2 and layout.shape[0] > 1:
        if np.any(layout < 0) or np.any(layout > 1):
            raise ValueError("layout coordinates must be between 0 and 1")
        if layout.shape[0] != nstate:
            raise ValueError("layout matrix should have one row per state")
        cbox = layout.astype(float).copy()
    else:
        lay = layout.reshape(-1).astype(float)
        if np.any(lay <= 0) or np.any(lay != np.floor(lay)):
            raise ValueError("non-integer number of states in layout argument")
        if int(np.sum(lay)) != nstate:
            raise ValueError("number of boxes != number of states")

        def space(n):
            return (np.arange(1, n + 1) - 0.5) / n

        cbox = np.zeros((nstate, 2))
        n = lay.size
        ix = np.repeat(np.arange(1, n + 1), lay.astype(int))
        if layout.ndim == 1 or layout.shape[1] > 1:
            # left to right: columns of boxes, centres spread over the columns
            cbox[:, 0] = space(n)[ix - 1]
            for i in range(1, n + 1):
                cbox[ix == i, 1] = 1 - space(int(lay[i - 1]))
        else:
            # top to bottom
            cbox[:, 1] = 1 - space(n)[ix - 1]
            for i in range(1, n + 1):
                cbox[ix == i, 0] = space(int(lay[i - 1]))

    for i in range(nstate):
        ax.text(
            cbox[i, 0],
            cbox[i, 1],
            statenames[i],
            fontsize=10 * cex,
            color=_r_color(col[i]),
            ha="center",
            va="center",
        )
    textwd = np.zeros(nstate)
    textht = np.zeros(nstate)
    fig = ax.figure
    pos = ax.get_position()
    pin_w = pos.width * fig.get_figwidth()
    pin_h = pos.height * fig.get_figheight()
    for i, name in enumerate(statenames):
        w_in, h_in = _text_extent(name, cex)
        textwd[i] = w_in / pin_w
        textht[i] = h_in / pin_h
    mean_pin = (pin_w + pin_h) / 2.0
    dx = margin * pin_h / mean_pin
    dy = margin * pin_w / mean_pin

    if box:
        for i in range(nstate):
            hx = textwd[i] / 2 + dx
            hy = textht[i] / 2 + dy
            xs = cbox[i, 0] + np.array([-hx, hx, hx, -hx, -hx])
            ys = cbox[i, 1] + np.array([-hy, -hy, hy, hy, -hy])
            ax.plot(xs, ys, color=_r_color(bcol[i]), linewidth=lwd[i], linestyle=_r_linestyle(lty[i]))
        dx = 2 * dx
        dy = 2 * dy

    def arrow2(x0, y0, x1, y1, lw, ls, color):
        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                linewidth=lw,
                linestyle=ls,
                shrinkA=0,
                shrinkB=0,
            ),
        )

    def doline(x1, x2, d, delta1, delta2, lw, ls, color):
        if d == 0 and x1[0] == x2[0]:
            if x1[1] > x2[1]:
                arrow2(x1[0], x1[1] - delta1[1], x2[0], x2[1] + delta2[1], lw, ls, color)
            else:
                arrow2(x1[0], x1[1] + delta1[1], x2[0], x2[1] - delta2[1], lw, ls, color)
        elif d == 0 and x1[1] == x2[1]:
            if x1[0] > x2[0]:
                arrow2(x1[0] - delta1[0], x1[1], x2[0] + delta2[0], x2[1], lw, ls, color)
            else:
                arrow2(x1[0] + delta1[0], x1[1], x2[0] - delta2[0], x2[1], lw, ls, color)
        else:
            temp = _phi(x1[0], x1[1], x2[0], x2[1], d, delta1, delta2)
            C = temp["center"]
            r = temp["r"]
            a = temp["angle"]
            if d == 0:
                arrow2(
                    C[0] + r * math.cos(a[0]),
                    C[1] + r * math.sin(a[0]),
                    C[0] + r * math.cos(a[1]),
                    C[1] + r * math.sin(a[1]),
                    lw,
                    ls,
                    color,
                )
            else:
                phi = np.linspace(a[0], a[1], 21)
                ax.plot(
                    C[0] + r * np.cos(phi),
                    C[1] + r * np.sin(phi),
                    linewidth=lw,
                    linestyle=ls,
                    color=color,
                )
                arrow2(
                    C[0] + r * math.cos(phi[19]),
                    C[1] + r * math.sin(phi[19]),
                    C[0] + r * math.cos(phi[20]),
                    C[1] + r * math.sin(phi[20]),
                    lw,
                    ls,
                    color,
                )

    k = 0
    for j in range(nstate):
        for i in range(nstate):
            if i != j and connect[i, j] != 0:
                delta1 = (textwd[i] / 2 + dx, textht[i] / 2 + dy)
                delta2 = (textwd[j] / 2 + dx, textht[j] / 2 + dy)
                if connect[i, j] == 2 - connect[j, i] and offset != 0:
                    toff = np.array([cbox[j, 1] - cbox[i, 1], cbox[i, 0] - cbox[j, 0]])
                    toff = -offset * toff / math.sqrt(np.sum(toff ** 2))
                    doline(
                        cbox[i] + toff,
                        cbox[j] + toff,
                        connect[i, j] - 1,
                        delta1,
                        delta2,
                        alwd[k],
                        _r_linestyle(alty[k]),
                        _r_color(acol[k]),
                    )
                else:
                    doline(
                        cbox[i],
                        cbox[j],
                        connect[i, j] - 1,
                        delta1,
                        delta2,
                        alwd[k],
                        _r_linestyle(alty[k]),
                        _r_color(acol[k]),
                    )
                k += 1
    return cbox


# ---------------------------------------------------------------------------
# pairs_grid: the panel layout of pairs() (graphics::pairs).
#
# R sets par(mfrow = c(n, n)), par(mar = gap/2 lines) and par(oma = 4 lines)
# and then draws panels in call order. This function creates the same n x n
# frame of Matplotlib axes, in the same visual order (row 0 at the top). The
# panel contents, the axis limits and the labels are the caller's.
# ---------------------------------------------------------------------------

_LINE_INCHES = 0.2  # one margin line at R's default 12-point device


def pairs_grid(fig, n, gap=0.2, oma_lines=4.0):
    """Return ``axes[row][col]`` for an n-by-n pairs layout on ``fig``.

    ``gap`` is the R ``gap`` argument in lines, and each panel has ``gap / 2``
    lines of margin on every side. ``oma_lines`` is the outer margin. Row 0 and
    column 0 are the top row and the left column.
    """
    width, height = fig.get_size_inches()
    outer = oma_lines * _LINE_INCHES
    margin = gap / 2.0 * _LINE_INCHES
    x_lo, x_hi = outer, width - outer
    y_lo, y_hi = outer, height - outer
    cell_w = (x_hi - x_lo) / n
    cell_h = (y_hi - y_lo) / n
    axes = []
    for row in range(n):
        line = []
        for col in range(n):
            left = x_lo + col * cell_w + margin
            bottom = y_hi - (row + 1) * cell_h + margin
            line.append(
                fig.add_axes(
                    [
                        left / width,
                        bottom / height,
                        (cell_w - 2 * margin) / width,
                        (cell_h - 2 * margin) / height,
                    ]
                )
            )
        axes.append(line)
    return axes


__all__ = ["fan", "statefig", "pairs_grid"]
