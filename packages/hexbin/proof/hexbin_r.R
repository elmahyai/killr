# R reference for hexbin(). Run from the repository root:
#   Rscript packages/hexbin/proof/hexbin_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
x <- p$x
y <- p$y

# case1: default shape, IDs kept.
h1 <- hexbin(x, y, xbins = 30, shape = 1, IDs = TRUE)
record_hexbin("case1", h1)

# case2: a different grid, no IDs.
h2 <- hexbin(x, y, xbins = 12, shape = 0.8)
record_hexbin("case2", h2)

# case3: NA in x and y, IDs kept, so cID carries NA at those points.
xna <- x
xna[c(5, 77)] <- NA
yna <- y
yna[300] <- NA
h3 <- hexbin(xna, yna, xbins = 30, shape = 1, IDs = TRUE)
record_hexbin("case3", h3)

# case4: explicit bounds, which must encompass the data.
h4 <- hexbin(x, y, xbins = 20, shape = 1.2, xbnds = c(-6, 6), ybnds = c(-4, 4))
record_hexbin("case4", h4)

record_timing(function() hexbin(x, y, xbins = 30, shape = 1))
write_ref("hexbin")
