# R reference for hcell2xy(). Run from the repository root:
#   Rscript packages/hexbin/proof/hcell2xy_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
h <- hexbin(p$x, p$y, xbins = 30, IDs = TRUE)
h2 <- hexbin(p$x, p$y, xbins = 12, shape = 0.8)
e <- erode(h, cdfcut = 0.5)

xy1 <- hcell2xy(h)
put_num("case1.x", xy1$x)
put_num("case1.y", xy1$y)

xy2 <- hcell2xy(h2)
put_num("case2.x", xy2$x)
put_num("case2.y", xy2$y)

# erodebin with the erosion check (default): only the eroded cells.
xy3 <- hcell2xy(e)
put_num("case3.x", xy3$x)
put_num("case3.y", xy3$y)

# erodebin with check.erosion = FALSE: every cell.
xy4 <- hcell2xy(e, check.erosion = FALSE)
put_num("case4.x", xy4$x)
put_num("case4.y", xy4$y)

record_timing(function() hcell2xy(h))
write_ref("hcell2xy")
