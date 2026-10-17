# R reference for getMargins(). Run from the repository root:
#   Rscript packages/hexbin/proof/getMargins_r.R
# getMargins() is an S4 generic, so it is called through the namespace with :::.
source("packages/hexbin/proof/_proof_common.R")
pdf(NULL)  # hexViewport() converts units, which needs a device; no file is written.

p <- points_fixed(200)
h <- hexbin(p$x, p$y, xbins = 12)
hv <- hexViewport(h, mar = grid::unit(c(3, 3, 3, 3), "lines"))
hv2 <- hexViewport(h, mar = grid::unit(c(1, 2, 1.5, 0.5), "lines"))
record_hexvp("hv", hv)
record_hexvp("hv2", hv2)

put_num("case1", hexbin:::getMargins(hv, ret.unit = "lines", numeric = TRUE))
put_num("case2", hexbin:::getMargins(hv2, ret.unit = "lines", numeric = TRUE))

record_timing(function() for (i in 1:2000) hexbin:::getMargins(hv, ret.unit = "lines", numeric = TRUE))
write_ref("getMargins")
