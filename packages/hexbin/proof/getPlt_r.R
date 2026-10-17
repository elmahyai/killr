# R reference for getPlt(). Run from the repository root:
#   Rscript packages/hexbin/proof/getPlt_r.R
# getPlt() is an S4 generic, so it is called through the namespace with :::.
source("packages/hexbin/proof/_proof_common.R")
pdf(NULL)  # hexViewport() converts units, which needs a device; no file is written.

p <- points_fixed(200)
h <- hexbin(p$x, p$y, xbins = 12)
hv <- hexViewport(h, mar = grid::unit(c(3, 3, 3, 3), "lines"))
hv2 <- hexViewport(h, mar = grid::unit(c(1, 2, 1.5, 0.5), "lines"))
record_hexvp("hv", hv)
record_hexvp("hv2", hv2)

put_num("case1", hexbin:::getPlt(hv, ret.unit = "npc", numeric = TRUE))
put_num("case2", hexbin:::getPlt(hv2, ret.unit = "npc", numeric = TRUE))
# The default ret.unit is "npc", the unit hexViewport() stores.
put_num("case3", hexbin:::getPlt(hv2, numeric = TRUE))

record_timing(function() for (i in 1:2000) hexbin:::getPlt(hv, ret.unit = "npc", numeric = TRUE))
write_ref("getPlt")
