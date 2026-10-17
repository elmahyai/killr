# R reference for inout.hex(). Run from the repository root:
#   Rscript packages/hexbin/proof/inout_hex_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
x <- p$x
y <- p$y

h <- hexbin(x, y, xbins = 30, IDs = TRUE)
put_num("case1", inout.hex(h, mincnt = 3))
put_num("case2", inout.hex(h, mincnt = 10))

h2 <- hexbin(x, y, xbins = 12, shape = 0.8, IDs = TRUE)
put_num("case3", inout.hex(h2, mincnt = 5))

# NA points: their cID is NA and is never reported.
xna <- x
xna[c(5, 77)] <- NA
hna <- hexbin(xna, y, xbins = 30, IDs = TRUE)
put_num("case4", inout.hex(hna, mincnt = 5))

record_timing(function() inout.hex(h, mincnt = 5))
write_ref("inout_hex")
