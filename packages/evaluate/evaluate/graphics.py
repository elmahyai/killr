"""Plot recording.

evaluate stores a base-graphics display list. Names that do not draw,
such as ``C_par`` and ``palette2``, match the installed package.
Matplotlib draws that list when a plot is replayed.
"""

from __future__ import annotations

from evaluate.state import STATE, dev_cur, run_hooks
from evaluate.types import Evaluation, GraphicsCall, Invisible, RecordedPlot, new_evaluation
from evaluate.show import as_list

NON_VISUAL = {
    "C_clip",
    "C_layout",
    "C_par",
    "C_plot_window",
    "C_strHeight",
    "C_strWidth",
    "palette",
    "palette2",
}


class Device:
    def __init__(self) -> None:
        self.dl: list[GraphicsCall] = []
        self.nfig = 1
        self.filled = 0

    def page(self) -> bool:
        if self.nfig <= 1:
            return True
        if self.filled <= 0:
            return True
        return self.filled >= self.nfig

    def plot_new(self) -> None:
        run_hooks("before.plot.new")
        new_page = self.nfig <= 1 or self.filled == 0 or self.filled >= self.nfig
        if new_page:
            self.dl = []
            self.filled = 0
        self.dl.append(GraphicsCall("C_plot_new"))
        self.filled += 1


def ensure_device() -> Device:
    current = dev_cur()
    if current is None:
        current = Device()
        STATE.devices.append(current)
    return current


def _nums(value) -> list[float]:
    return [float(item) for item in as_list(value)]


def xy_coords(x, y=None) -> tuple[list[float], list[float]]:
    xs = _nums(x)
    if y is None:
        ys = xs
        xs = [float(i) for i in range(1, len(ys) + 1)]
        return xs, ys
    return xs, _nums(y)


def plot(x, y=None, main="", xlab="", ylab="", **_kwargs):
    xs, ys = xy_coords(x, y)
    dev = ensure_device()
    dev.plot_new()
    finite_x = xs or [0.0]
    finite_y = ys or [0.0]
    dev.dl.append(GraphicsCall("palette2"))
    dev.dl.append(
        GraphicsCall(
            "C_plot_window",
            xlim=(min(finite_x), max(finite_x)),
            ylim=(min(finite_y), max(finite_y)),
        )
    )
    dev.dl.append(GraphicsCall("C_plotXY", x=xs, y=ys))
    dev.dl.append(GraphicsCall("C_axis"))
    dev.dl.append(GraphicsCall("C_axis"))
    dev.dl.append(GraphicsCall("C_box"))
    dev.dl.append(GraphicsCall("C_title", main=str(main)))
    if STATE.watcher is None:
        draw_plot(RecordedPlot(dev.dl))
    return Invisible(None)


def plot_new():
    dev = ensure_device()
    dev.plot_new()
    return Invisible(None)


def text(x, y=None, labels="", **_kwargs):
    if y is None:
        raise TypeError("text() needs x and y")
    dev = ensure_device()
    xs = _nums(x)
    ys = _nums(y)
    labs = [str(item) for item in as_list(labels)]
    if len(labs) == 1 and len(xs) > 1:
        labs = labs * len(xs)
    dev.dl.append(GraphicsCall("C_text", x=xs, y=ys, labels=labs))
    return Invisible(None)


def lines(x, y=None, **_kwargs):
    xs, ys = xy_coords(x, y)
    dev = ensure_device()
    dev.dl.append(GraphicsCall("C_lines", x=xs, y=ys))
    return Invisible(None)


def points(x, y=None, **_kwargs):
    xs, ys = xy_coords(x, y)
    dev = ensure_device()
    dev.dl.append(GraphicsCall("C_points", x=xs, y=ys))
    return Invisible(None)


def par(*_args, **kwargs):
    dev = ensure_device()
    if "mfrow" in kwargs:
        value = kwargs["mfrow"]
        rows, cols = as_list(value)
        dev.nfig = int(rows) * int(cols)
        dev.filled = 0
    dev.dl.append(GraphicsCall("C_par"))
    return Invisible(None)


def makes_visual_change(display_list) -> bool:
    for call in display_list:
        if call.name not in NON_VISUAL:
            return True
    return False


def is_prefix(old, new) -> bool:
    if len(old) > len(new):
        return False
    return list(old) == list(new[: len(old)])


def looks_different(old, new) -> bool:
    if old is None:
        return True
    if not is_prefix(old, new):
        return True
    return makes_visual_change(new[len(old) :])


def trim_intermediate_plots(x):
    if not isinstance(x, Evaluation):
        raise ValueError("`x` must be an evaluation object.")
    plot_idx = [i for i, item in enumerate(x) if isinstance(item, RecordedPlot)]
    keep = [True] * len(plot_idx)
    for i in range(1, len(plot_idx)):
        prev = x[plot_idx[i - 1]].dl
        cur = x[plot_idx[i]].dl
        if is_prefix(prev, cur):
            keep[i - 1] = False
    drop = {plot_idx[i] for i, flag in enumerate(keep) if not flag}
    return new_evaluation([item for i, item in enumerate(x) if i not in drop])


def draw_plot(plot: RecordedPlot):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _fig, ax = plt.subplots()
    for call in plot.dl:
        data = call.data
        if call.name in {"C_plotXY", "C_points"}:
            ax.plot(data.get("x", ()), data.get("y", ()), "o")
        elif call.name == "C_lines":
            ax.plot(data.get("x", ()), data.get("y", ()), "-")
        elif call.name == "C_text":
            labels = data.get("labels", ())
            xs = data.get("x", ())
            ys = data.get("y", ())
            for x, y, label in zip(xs, ys, labels):
                ax.text(x, y, label)
        elif call.name == "C_title":
            main = data.get("main")
            if main:
                ax.set_title(main)
    return ax.figure
