# R reference for erode.hexbin(), the hexbin method called directly. Run from the repository root:
#   Rscript packages/hexbin/proof/erode_hexbin_r.R
source("packages/hexbin/proof/_proof_common.R")

record_erode <- function(prefix, e) {
  if (is.character(e)) {
    put_str(paste0(prefix, ".result"), e)
    return(invisible(NULL))
  }
  put_num(paste0(prefix, ".cell"), e@cell)
  put_num(paste0(prefix, ".count"), e@count)
  put_num(paste0(prefix, ".eroded"), as.numeric(e@eroded))
  put_num(paste0(prefix, ".erode"), e@erode)
  put_num(paste0(prefix, ".cdfcut"), e@cdfcut)
  put_num(paste0(prefix, ".dimen"), e@dimen)
  invisible(NULL)
}

p <- points_fixed(20000)
h <- hexbin(p$x, p$y, xbins = 30, IDs = TRUE)
h2 <- hexbin(p$x, p$y, xbins = 12, shape = 0.8)
h3 <- hexbin(p$x, p$y, xbins = 30)

record_erode("case1", erode.hexbin(h, cdfcut = 0.5))
record_erode("case2", erode.hexbin(h2, cdfcut = 0.75))
record_erode("case3", erode.hexbin(h3, cdfcut = 2))   # no cell reaches the cut: a string
record_erode("case4", erode.hexbin(h, cdfcut = 0.1))

record_timing(function() erode.hexbin(h, cdfcut = 0.5))
write_ref("erode_hexbin")
