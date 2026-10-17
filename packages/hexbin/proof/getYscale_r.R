# R reference for getYscale(). Run from the repository root:
#   Rscript packages/hexbin/proof/getYscale_r.R
# hexbin 1.28.6 comments out the getYscale generic. Its body, x@yscale, is the reference here.
source("packages/hexbin/proof/_proof_common.R")
pdf(NULL)  # hexViewport() converts units, which needs a device; no file is written.

p <- points_fixed(200)
h <- hexbin(p$x, p$y, xbins = 12)
hv <- hexViewport(h, mar = grid::unit(c(3, 3, 3, 3), "lines"))
hv2 <- hexViewport(h, mar = grid::unit(c(1, 2, 1.5, 0.5), "lines"), ybnds = c(-4, 4))
record_hexvp("hv", hv)
record_hexvp("hv2", hv2)

put_num("case1", hv@yscale)
put_num("case2", hv2@yscale)

record_timing(function() for (i in 1:2000) hv@yscale)
write_ref("getYscale")
