"""Map panel coordinates to conditioning packet indices, as lattice does."""

from __future__ import annotations

import math


def packet_panel_default(
    layout,
    condlevels,
    page,
    row,
    column,
    skip,
    all_pages_skip=True,
):
    """Return level indices for the packet drawn at ``page``, ``row``, ``column``."""
    ncol, nrow = int(layout[0]), int(layout[1])
    panels_per_page = ncol * nrow
    panels_per_row = ncol

    packet_order = _expand_grid(condlevels)
    skip = _expand_skip(skip, panels_per_page, int(page), all_pages_skip)

    panel_number = (
        1
        + (int(page) - 1) * panels_per_page
        + (int(row) - 1) * panels_per_row
        + (int(column) - 1)
    )

    if skip[panel_number - 1]:
        return None

    panel_number -= sum(skip[:panel_number])
    if panel_number > len(packet_order):
        return None

    return [float(value) for value in packet_order[panel_number - 1]]


def _expand_grid(condlevels):
    if not condlevels:
        return []
    sizes = [len(levels) for levels in condlevels]
    total = math.prod(sizes)
    rows = []
    for index in range(total):
        row = []
        for level_index, levels in enumerate(condlevels):
            stride = math.prod(sizes[:level_index]) if level_index else 1
            row.append(levels[(index // stride) % len(levels)])
        rows.append(row)
    return rows


def _expand_skip(skip, panels_per_page, page, all_pages_skip):
    skip = list(skip)
    if all_pages_skip:
        length = panels_per_page * page
        if len(skip) < length:
            skip = (skip * ((length + len(skip) - 1) // len(skip)))[:length]
        else:
            skip = skip[:length]
    else:
        if len(skip) < panels_per_page:
            skip = (skip * ((panels_per_page + len(skip) - 1) // len(skip)))[:panels_per_page]
        else:
            skip = skip[:panels_per_page]
        skip = skip * page
    return skip
