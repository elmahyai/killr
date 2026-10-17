"""R graphics devices: named gaps, not translated as drawing code.

with_bmp, with_png and the rest open an R graphics device (grDevices), draw
into it, and close it. A device is drawing code, so it is not translated here.
Charts route to Matplotlib or a killplot function, per CONSTITUTION.md.
"""

from ._gap import stub

_REASON = (
    "the R device grDevices::{device} draws into a file, and drawing code is not "
    "translated; charts route to Matplotlib or killplot"
)

with_bmp = stub("with_bmp", _REASON.format(device="bmp"))
local_bmp = stub("local_bmp", _REASON.format(device="bmp"))
with_cairo_pdf = stub("with_cairo_pdf", _REASON.format(device="cairo_pdf"))
local_cairo_pdf = stub("local_cairo_pdf", _REASON.format(device="cairo_pdf"))
with_cairo_ps = stub("with_cairo_ps", _REASON.format(device="cairo_ps"))
local_cairo_ps = stub("local_cairo_ps", _REASON.format(device="cairo_ps"))
with_jpeg = stub("with_jpeg", _REASON.format(device="jpeg"))
local_jpeg = stub("local_jpeg", _REASON.format(device="jpeg"))
with_pdf = stub("with_pdf", _REASON.format(device="pdf"))
local_pdf = stub("local_pdf", _REASON.format(device="pdf"))
with_png = stub("with_png", _REASON.format(device="png"))
local_png = stub("local_png", _REASON.format(device="png"))
with_postscript = stub("with_postscript", _REASON.format(device="postscript"))
local_postscript = stub("local_postscript", _REASON.format(device="postscript"))
with_svg = stub("with_svg", _REASON.format(device="svg"))
local_svg = stub("local_svg", _REASON.format(device="svg"))
with_tiff = stub("with_tiff", _REASON.format(device="tiff"))
local_tiff = stub("local_tiff", _REASON.format(device="tiff"))
with_xfig = stub("with_xfig", _REASON.format(device="xfig"))
local_xfig = stub("local_xfig", _REASON.format(device="xfig"))
