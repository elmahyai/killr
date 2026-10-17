"""Steady-state plots.

``plot.steady1D`` draws one line per species. ``image.steady2D`` and
``image.steady3D`` draw the state the way R's ``image`` does: the first
matrix index runs along x, the second along y, and a missing grid is
``seq(0, 1, length.out = n)``. ``which`` is 1-based, as in R.
"""

import matplotlib

matplotlib.use("Agg", force=False)

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

_BLUE_RED = LinearSegmentedColormap.from_list(
    "BlueRed",
    ["#00007F", "blue", "#007FFF", "cyan", "#7FFF7F", "yellow",
     "#FF7F00", "red", "#7F0000"],
)


class Drawn:
    """A figure plus the coordinates that were drawn."""

    def __init__(self, figure, coordinates):
        self.figure = figure
        self.coordinates = coordinates

    def __str__(self):
        lines = []
        for item in self.coordinates:
            lines.append(item["name"])
            if "x" in item:
                lines.append("x " + " ".join(f"{value:.7g}" for value in item["x"]))
                lines.append("y " + " ".join(f"{value:.7g}" for value in item["y"]))
            if "z" in item:
                flat = np.ravel(item["z"], order="F")
                lines.append("z " + " ".join(f"{value:.7g}" for value in flat))
        return "\n".join(lines)


def _species_matrix(result):
    nspec = result.nspec if result.nspec is not None else 1
    values = np.asarray(result.y.values, dtype=float)
    if values.size % nspec != 0:
        raise ValueError(
            "length of 'x' should be a multiple of 'nspec' if x is a vector"
        )
    return values.reshape((values.size // nspec, nspec), order="F")


def _blocks(result):
    """One column-major array per species, shaped by ``dimens``."""
    nspec = result.nspec if result.nspec is not None else 1
    dimens = result.dimens
    if dimens is None:
        raise ValueError("dimens is missing")
    shape = tuple(int(item) for item in np.atleast_1d(dimens))
    values = np.asarray(result.y.values, dtype=float)
    volume = int(np.prod(shape))
    if values.size != nspec * volume:
        raise ValueError(
            "length of 'x' should be = 'nspec' * prod(dimens) if x is a vector"
        )
    names = result.ynames
    if names is None:
        names = [str(index) for index in range(1, nspec + 1)]
    blocks = []
    for index in range(nspec):
        piece = values[index * volume:(index + 1) * volume]
        blocks.append(piece.reshape(shape, order="F"))
    return blocks, [str(name) for name in names]


def _select(which, names):
    if which is None:
        return list(range(len(names)))
    if isinstance(which, (str, bytes)):
        which = [which]
    chosen = []
    if isinstance(which, (int, np.integer)):
        which = [int(which)]
    for item in which:
        if isinstance(item, str):
            if item not in names:
                raise ValueError(f"variable {item} not in variable names")
            chosen.append(names.index(item))
        else:
            index = int(item)
            if index < 1:
                raise ValueError("index in 'which' should be > 0")
            if index > len(names):
                raise ValueError("index in 'which' too large")
            chosen.append(index - 1)
    return chosen


def _image_axes(nrow, ncol, grid):
    if grid is None:
        x = np.linspace(0.0, 1.0, nrow)
        y = np.linspace(0.0, 1.0, ncol)
    else:
        x = np.asarray(grid[0], dtype=float)
        y = np.asarray(grid[1], dtype=float)
    return x, y


def plot_steady1d(x, which=None, grid=None, xyswap=False, vertical=False,
                  obs=None, **kwargs):
    """Line plot of a 1-D steady state. The default grid is the row index."""
    if grid is not None and np.asarray(grid).ndim != 1:
        raise ValueError("'grid' should be a vector")
    matrix = _species_matrix(x)
    if x.ynames is None:
        names = [str(index) for index in range(1, matrix.shape[1] + 1)]
    else:
        names = [str(name) for name in x.ynames]
    # A matrix with one column per species. Names label those columns.
    if x.ynames is not None and len(names) == matrix.shape[1]:
        pass
    chosen = _select(which, names)
    if not chosen:
        raise ValueError("nothing to plot")
    if grid is None:
        axis = np.arange(1, matrix.shape[0] + 1, dtype=float)
    else:
        axis = np.asarray(grid, dtype=float)
        if axis.size != matrix.shape[0]:
            raise ValueError(
                "length of grid (x-axis) should be = number of rows in 'x$y'"
            )
    figure, axes = plt.subplots(len(chosen), 1, squeeze=False, figsize=(6, 3 * len(chosen)))
    coordinates = []
    for slot, index in enumerate(chosen):
        ax = axes[slot, 0]
        column = matrix[:, index]
        if xyswap:
            drawn_x, drawn_y = column, axis
            ax.set_xlabel("")
            ax.set_ylabel("")
            if vertical:
                ax.set_ylim(axis[-1], axis[0])
        else:
            drawn_x, drawn_y = axis, column
            # R swaps the default labels, so "x" ends on the vertical axis.
            ax.set_xlabel(kwargs.get("xlab", ""))
            ax.set_ylabel(kwargs.get("ylab", "x"))
        ax.plot(drawn_x, drawn_y, color="black")
        ax.set_title(kwargs.get("main", names[index]))
        coordinates.append({
            "name": names[index],
            "x": np.asarray(drawn_x, dtype=float),
            "y": np.asarray(drawn_y, dtype=float),
        })
    figure.tight_layout()
    return Drawn(figure, coordinates)


def image_steady2d(x, which=None, add_contour=False, grid=None, legend=False,
                   method="image", **kwargs):
    """Image of one 2-D species. ``which`` selects a single variable by default all."""
    blocks, names = _blocks(x)
    chosen = _select(which, names)
    if len(chosen) > 1 and which is None:
        pass
    figure, axes = plt.subplots(
        len(chosen), 1, squeeze=False, figsize=(5, 4 * max(len(chosen), 1)),
    )
    coordinates = []
    for slot, index in enumerate(chosen):
        ax = axes[slot, 0]
        z = np.asarray(blocks[index], dtype=float)
        xs, ys = _image_axes(z.shape[0], z.shape[1], grid)
        extent = (xs[0], xs[-1], ys[0], ys[-1])
        # Transpose so the first index is horizontal, matching image().
        ax.imshow(
            z.T, origin="lower", extent=extent, aspect="auto",
            cmap=_BLUE_RED, interpolation="nearest",
        )
        if add_contour:
            ax.contour(xs, ys, z.T, colors="black")
        if legend:
            figure.colorbar(ax.images[0], ax=ax)
        ax.set_title(kwargs.get("main", names[index]))
        ax.set_xlabel(kwargs.get("xlab", "x"))
        ax.set_ylabel(kwargs.get("ylab", "y"))
        coordinates.append({
            "name": names[index],
            "x": xs,
            "y": ys,
            "z": z,
        })
    figure.tight_layout()
    return Drawn(figure, coordinates)


def image_steady3d(x, which=None, dimselect=None, add_contour=False, grid=None,
                   legend=False, method="image", **kwargs):
    """One 2-D image per selected plane of a 3-D steady state."""
    blocks, names = _blocks(x)
    chosen = _select(which, names)
    if dimselect is None:
        axis = 2
        picks = list(range(1, blocks[0].shape[2] + 1))
    elif "z" in dimselect:
        axis = 2
        picks = [int(item) for item in np.atleast_1d(dimselect["z"])]
    elif "y" in dimselect:
        axis = 1
        picks = [int(item) for item in np.atleast_1d(dimselect["y"])]
    elif "x" in dimselect:
        axis = 0
        picks = [int(item) for item in np.atleast_1d(dimselect["x"])]
    else:
        raise ValueError("dimselect needs x, y, or z")
    limit = blocks[0].shape[axis]
    if max(picks) > limit:
        raise ValueError(
            "Numbers in 'dimselect' can not be larger than corresponding dimension"
        )
    if min(picks) < 1:
        raise ValueError("Numbers in 'zselect' can not be < 1")
    figure, axes = plt.subplots(
        len(picks) * len(chosen), 1, squeeze=False,
        figsize=(5, 3.5 * len(picks) * len(chosen)),
    )
    coordinates = []
    slot = 0
    for plane in picks:
        for index in chosen:
            block = blocks[index]
            if axis == 2:
                z = block[:, :, plane - 1]
            elif axis == 1:
                z = block[:, plane - 1, :]
            else:
                z = block[plane - 1, :, :]
            ax = axes[slot, 0]
            xs, ys = _image_axes(z.shape[0], z.shape[1], grid)
            extent = (xs[0], xs[-1], ys[0], ys[-1])
            ax.imshow(
                z.T, origin="lower", extent=extent, aspect="auto",
                cmap=_BLUE_RED, interpolation="nearest",
            )
            if add_contour:
                ax.contour(xs, ys, z.T, colors="black")
            title = kwargs.get("main", f"var {names[index]} dim {axis + 1} = {plane}")
            ax.set_title(title)
            coordinates.append({
                "name": f"{names[index]}:{plane}",
                "x": xs,
                "y": ys,
                "z": np.asarray(z, dtype=float),
            })
            slot += 1
    figure.tight_layout()
    return Drawn(figure, coordinates)


def subset_steady2d(x, which=None, **kwargs):
    """One species of a 2-D steady state, as a column-major matrix."""
    blocks, names = _blocks(x)
    if which is None:
        which = list(range(1, len(names) + 1))
    chosen = _select(which, names)
    if len(chosen) > 1:
        raise ValueError("Can only select one variable")
    return blocks[chosen[0]]
