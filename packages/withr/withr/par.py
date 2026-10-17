"""with_par and local_par (R's par.R): graphics parameters.

par() reads and sets the state of R's graphics device. There is no such device
state in Python, so these are a named gap.
"""

from ._gap import stub

_REASON = "graphics parameters belong to R's graphics device state, which is not translated"

with_par = stub("with_par", _REASON)
local_par = stub("local_par", _REASON)
