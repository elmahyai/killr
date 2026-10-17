"""A horizontal or vertical reference line.

The R function returns a ggplot2 layer. This returns the same intercept
and draws it with Matplotlib when draw() is asked to.
"""

from __future__ import annotations

_MISSING = object()


class RefLine:
    def __init__(self, direction, value, size, colour):
        self.direction = direction
        self.value = value
        self.size = size
        self.colour = colour

    def draw(self, path=None):
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots()
        pad = 1.0
        if self.colour == "white":
            axes.set_facecolor("#333333")
        if self.direction == "h":
            axes.set_xlim(0, 1)
            axes.set_ylim(self.value - pad, self.value + pad)
            axes.axhline(self.value, color=self.colour, linewidth=self.size)
        else:
            axes.set_ylim(0, 1)
            axes.set_xlim(self.value - pad, self.value + pad)
            axes.axvline(self.value, color=self.colour, linewidth=self.size)
        if path is not None:
            figure.savefig(path, format="svg")
        plt.close(figure)
        return self.value

    def __str__(self):
        kind = "horizontal" if self.direction == "h" else "vertical"
        return f"{kind} reference line at {self.value}"


def geom_ref_line(h=_MISSING, v=_MISSING, size=2, colour="white"):
    if h is not _MISSING:
        return RefLine("h", h, size, colour)
    if v is not _MISSING:
        return RefLine("v", v, size, colour)
    raise ValueError("Must supply one of `h` and `v`.")
