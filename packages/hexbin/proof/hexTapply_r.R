# R reference for hexTapply(). Run from the repository root:
#   Rscript packages/hexbin/proof/hexTapply_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
x <- p$x
y <- p$y
h <- hexbin(x, y, xbins = 30, IDs = TRUE)

r1 <- hexTapply(h, y, FUN = sum)
put_num("case1.keys", as.numeric(names(r1)))
put_num("case1.values", as.numeric(r1))

r2 <- hexTapply(h, x, FUN = mean)
put_num("case2.keys", as.numeric(names(r2)))
put_num("case2.values", as.numeric(r2))

r3 <- hexTapply(h, x, FUN = max)
put_num("case3.keys", as.numeric(names(r3)))
put_num("case3.values", as.numeric(r3))

record_timing(function() hexTapply(h, x, FUN = sum))
write_ref("hexTapply")
