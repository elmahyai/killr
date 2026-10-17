"""Trellis plots from lattice 0.23-1.

The high-level charts evaluate the formula, the packets, and the scales
the way lattice does. Matplotlib draws the figure. grid is not used.
"""

from lattice.core import (
    Trellis,
    as_factor_or_shingle,
    banking,
    bwplot,
    do_breaks,
    lattice_parse_formula,
    panel_bwplot,
    panel_lmline,
    panel_xyplot,
    prepanel_default_xyplot,
    rows,
    trellis_par_get,
    xyplot,
)

__all__ = [
    "Trellis",
    "as_factor_or_shingle",
    "banking",
    "bwplot",
    "do_breaks",
    "lattice_parse_formula",
    "panel_bwplot",
    "panel_lmline",
    "panel_xyplot",
    "prepanel_default_xyplot",
    "rows",
    "trellis_par_get",
    "xyplot",
    "as_shingle",
    "lattice_options",
    "is_shingle",
    "lattice_get_option",
    "equal_count",
    "make_groups",
    "packet_panel_default",
    "trellis_last_object",
    "which_packet",
    "shingle",
    "current_column",
    "xscale_components_default",
]
from lattice.as_shingle import as_shingle
from lattice.lattice_options import lattice_options
from lattice.is_shingle import is_shingle
from lattice.lattice_get_option import lattice_get_option
from lattice.equal_count import equal_count
from lattice.make_groups import make_groups
from lattice.packet_panel_default import packet_panel_default
from lattice.trellis_last_object import trellis_last_object
from lattice.which_packet import which_packet
from lattice.shingle import shingle
from lattice.current_column import current_column
from lattice.xscale_components_default import xscale_components_default
