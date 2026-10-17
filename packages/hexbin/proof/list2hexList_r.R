# R reference for list2hexList(). Run from the repository root:
#   Rscript packages/hexbin/proof/list2hexList_r.R
source("packages/hexbin/proof/_proof_common.R")

p <- points_fixed(20000)
x <- p$x
y <- p$y
k <- as.numeric(1:length(x))
g <- c("alpha", "beta", "gamma")[(k %% 3) + 1]

# Same bounds in every object, as list2hexList requires.
hb_a <- hexbin(x[g == "alpha"], y[g == "alpha"], xbins = 30, xbnds = c(-5, 5), ybnds = c(-3, 3))
hb_b <- hexbin(x[g == "beta"], y[g == "beta"], xbins = 30, xbnds = c(-5, 5), ybnds = c(-3, 3))
hb_c <- hexbin(x[g == "gamma"], y[g == "gamma"], xbins = 30, xbnds = c(-5, 5), ybnds = c(-3, 3))

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

l3 <- list(alpha = hb_a, beta = hb_b, gamma = hb_c)
record_list("case1", list2hexList(l3))

l2 <- list(first = hb_a, second = hb_c)
record_list("case2", list2hexList(l2))

record_timing(function() list2hexList(l3))
write_ref("list2hexList")
