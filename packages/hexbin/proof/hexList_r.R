# R reference for hexList(). Run from the repository root:
#   Rscript packages/hexbin/proof/hexList_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
x <- p$x
y <- p$y
k <- as.numeric(1:length(x))
given <- c("alpha", "beta", "gamma")[(k %% 3) + 1]

record_list <- function(prefix, hl) {
  put_num(paste0(prefix, ".n"), hl@n)
  put_num(paste0(prefix, ".Xbnds"), hl@Xbnds)
  put_num(paste0(prefix, ".Ybnds"), hl@Ybnds)
  put_num(paste0(prefix, ".Xbins"), hl@Xbins)
  put_num(paste0(prefix, ".Shape"), hl@Shape)
  put_num(paste0(prefix, ".CntBnds"), hl@CntBnds)
  put_str(paste0(prefix, ".Bnames"), paste(hl@Bnames, collapse = "|"))
  for (i in seq_along(hl@hbins)) {
    record_hexbin(paste0(prefix, ".hb", i), hl@hbins[[i]])
  }
}

hl1 <- hexList(x, y, given, xbins = 30)
record_list("case1", hl1)

hl2 <- hexList(x, y, given, xbins = 12, shape = 0.8, xbnds = c(-5, 5), ybnds = c(-3, 3))
record_list("case2", hl2)

record_timing(function() hexList(x, y, given, xbins = 30))
write_ref("hexList")
