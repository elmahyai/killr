"""plot.xts and the panel helpers. The chart is a Matplotlib line."""

from __future__ import annotations

import io

from xts.series import Xts

_CURRENT = None


class _Panel:
    def __init__(self, low: float, high: float) -> None:
        self.ylim = (low, high)


class Plot:
    """The limits and panels of the current xts chart."""

    def __init__(self, series: Xts) -> None:
        values = [item for item in series.columns[0] if item is not None]
        low = min(values) if values else 0.0
        high = max(values) if values else 1.0
        self.series = series
        self.panels = [_Panel(low, high)]
        self.actions = 4
        self.xlim = (series.index[0], series.index[-1]) if series.index else (0.0, 1.0)
        self._draw(series.index, series.columns[0])

    def ylim(self):
        panel = self.panels[-1]
        return panel.ylim

    def _draw(self, stamps, values) -> None:
        import matplotlib

        matplotlib.use("Agg", force=False)
        import matplotlib.pyplot as plt

        figure, axis = plt.subplots()
        axis.plot(list(stamps), [float("nan") if value is None else value for value in values])
        axis.set_xlim(*self.xlim)
        axis.set_ylim(*self.ylim())
        buffer = io.BytesIO()
        figure.savefig(buffer, format="svg")
        plt.close(figure)
        self.svg = buffer.getvalue()


def _current() -> Plot:
    if _CURRENT is None:
        raise RuntimeError("no current xts plot")
    return _CURRENT


def plot_xts(x: Xts, y=None, **kwargs) -> str:
    """Draw the series and return the x and y limits."""
    del y, kwargs
    global _CURRENT
    _CURRENT = Plot(x)
    low, high = _CURRENT.xlim
    bottom, top = _CURRENT.ylim()
    return f"{low:.0f}|{high:.0f}|{bottom:.10g}|{top:.10g}"


def add_series(x: Xts, main: str = "", on=None, type: str = "l", **kwargs) -> str:
    """Add a series on a new panel. The result is that panel's y limits."""
    del main, on, type, kwargs
    plot = _current()
    values = [item for item in x.columns[0] if item is not None]
    plot.panels.append(_Panel(min(values), max(values)))
    plot._draw(x.index, x.columns[0])
    bottom, top = plot.ylim()
    return f"{bottom:.10g}|{top:.10g}"


def add_panel(fun, main: str = "", on=None, **kwargs) -> str:
    """Add a panel. The result is the panel count."""
    del main, on, kwargs
    plot = _current()
    produced = fun(plot.series)
    if isinstance(produced, Xts):
        values = [item for item in produced.columns[0] if item is not None]
        plot.panels.append(_Panel(min(values), max(values)))
    else:
        plot.panels.append(_Panel(*plot.panels[-1].ylim))
    return str(len(plot.panels))


def add_legend(legend_loc: str = "topright", legend_names=None, col=None, ncol: int = 1, on: int = 0, **kwargs) -> str:
    """Record a legend on the current panel. The result is the action count."""
    del legend_names, col, ncol, on, kwargs
    plot = _current()
    plot.actions += 1
    plot.legend_loc = legend_loc
    return str(plot.actions)


def add_event_lines(events: Xts, main: str = "", on: int = 0, **kwargs) -> str:
    """Mark event times on the current panel. The result is the action count."""
    del main, on, kwargs
    plot = _current()
    plot.actions += 1
    plot.events = list(events.index)
    return str(plot.actions)


def add_polygon(x: Xts, y=None, main: str = "", on=None, col=None, **kwargs) -> str:
    """Draw a polygon from the first two columns. The result is the new y limits."""
    del y, main, on, col, kwargs
    plot = _current()
    values = [item for column in x.columns[:2] for item in column if item is not None]
    plot.panels.append(_Panel(min(values), max(values)))
    plot._draw(x.index, x.columns[0])
    bottom, top = plot.ylim()
    return f"{bottom:.10g}|{top:.10g}"
