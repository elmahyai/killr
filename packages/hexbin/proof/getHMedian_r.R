# R reference for getHMedian(). Run from the repository root:
#   Rscript packages/hexbin/proof/getHMedian_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
h <- hexbin(p$x, p$y, xbins = 30, IDs = TRUE)
h2 <- hexbin(p$x, p$y, xbins = 12, shape = 0.8)

m1 <- getHMedian(erode(h, cdfcut = 0.5))
put_num("case1.x", m1$x)
put_num("case1.y", m1$y)

m2 <- getHMedian(erode(h2, cdfcut = 0.25))
put_num("case2.x", m2$x)
put_num("case2.y", m2$y)

m3 <- getHMedian(erode(h, cdfcut = 0.9))
put_num("case3.x", m3$x)
put_num("case3.y", m3$y)

e <- erode(h, cdfcut = 0.5)
record_timing(function() getHMedian(e))
write_ref("getHMedian")
