# R reference for optShape(). Run from the repository root:
#   Rscript packages/hexbin/proof/optShape_r.R
source("packages/hexbin/proof/_proof_common.R")

put_num("case1", optShape(height = 6, width = 4))
put_num("case2", optShape(height = 6, width = 4, mar = c(1, 0.5, 1, 0.5)))
put_num("case3", optShape(height = 2.5, width = 7, mar = c(0.2, 0.3, 0.4, 0.5)))
put_num("case4", optShape(height = 1, width = 3))

# A hexVP: the ratio of its plt slot, in npc, which hexViewport() stores.
pdf(NULL)  # hexViewport() converts units, which needs a device; no file is written.
p <- points_fixed(200)
hv <- hexViewport(hexbin(p$x, p$y, xbins = 12), mar = grid::unit(c(3, 3, 3, 3), "lines"))
record_hexvp("opt.hv", hv)
put_num("case5", optShape(hv))

record_timing(function() {
  for (i in 1:2000) optShape(height = 6, width = 4, mar = c(1, 0.5, 1, 0.5))
})
write_ref("optShape")
