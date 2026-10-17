"""Graphical HCL color chooser (colorspace 2.1-4)."""

from __future__ import annotations

from colorspace.hcl_color_picker import hcl_color_picker


def choose_color(shiny_trace=False):
    """Open the HCL color picker and return the selected color."""
    return hcl_color_picker(shiny_trace=shiny_trace)
