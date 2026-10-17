"""Python translation of the R package clipr."""

from clipr.clear_clip import clear_clip
from clipr.clipr_available import clipr_available
from clipr.dr_clipr import dr_clipr
from clipr.read_clip import read_clip
from clipr.read_clip_tbl import read_clip_tbl
from clipr.write_clip import write_clip
from clipr.write_last_clip import write_last_clip
from clipr._render import Frame, Matrix

__all__ = [
    "Frame",
    "Matrix",
    "clear_clip",
    "clipr_available",
    "dr_clipr",
    "read_clip",
    "read_clip_tbl",
    "write_clip",
    "write_last_clip",
]
