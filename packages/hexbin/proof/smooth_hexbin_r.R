# R reference for smooth.hexbin(), called directly, with its default weights in one case.
# Run from the repository root:
#   Rscript packages/hexbin/proof/smooth_hexbin_r.R
source("packages/hexbin/proof/_proof_common.R")

record_smooth <- function(prefix, s) {
  put_num(paste0(prefix, ".cell"), s@cell)
  put_num(paste0(prefix, ".count"), s@count)
  put_num(paste0(prefix, ".xcm"), s@xcm)
  put_num(paste0(prefix, ".ycm"), s@ycm)
  put_num(paste0(prefix, ".xbins"), s@xbins)
  put_num(paste0(prefix, ".xbnds"), s@xbnds)
  put_num(paste0(prefix, ".ybnds"), s@ybnds)
  put_num(paste0(prefix, ".dimen"), s@dimen)
  put_num(paste0(prefix, ".wts"), s@wts)
  put_num(paste0(prefix, ".n"), s@n)
  put_num(paste0(prefix, ".ncells"), s@ncells)
}

p <- points_fixed(20000)
h <- hexbin(p$x, p$y, xbins = 30)
h2 <- hexbin(p$x, p$y, xbins = 12, shape = 0.8)

record_smooth("case1", smooth.hexbin(h))                      # default wts = c(48, 4, 1)
record_smooth("case2", smooth.hexbin(h, wts = c(10, 3, 1)))
record_smooth("case3", smooth.hexbin(h2, wts = c(48, 4, 1)))

record_timing(function() smooth.hexbin(h))
write_ref("smooth_hexbin")
