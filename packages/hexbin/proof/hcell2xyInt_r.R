# R reference for hcell2xyInt(). Run from the repository root:
#   Rscript packages/hexbin/proof/hcell2xyInt_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
h <- hexbin(p$x, p$y, xbins = 30, IDs = TRUE)
h2 <- hexbin(p$x, p$y, xbins = 12, shape = 0.8)

r1 <- hcell2xyInt(h)
put_num("case1.i", r1$i)
put_num("case1.j", r1$j)

r2 <- hcell2xyInt(h2)
put_num("case2.i", r2$i)
put_num("case2.j", r2$j)

# No hexbin object: the grid comes from xbins, shape and the bounds.
r3 <- hcell2xyInt(xbins = 30, xbnds = c(-5, 5), ybnds = c(-3, 3), shape = 1)
put_num("case3.i", r3$i)
put_num("case3.j", r3$j)

r4 <- hcell2xyInt(xbins = 12, xbnds = c(-5, 5), ybnds = c(-3, 3), shape = 0.8)
put_num("case4.i", r4$i)
put_num("case4.j", r4$j)

record_timing(function() hcell2xyInt(h))
write_ref("hcell2xyInt")
