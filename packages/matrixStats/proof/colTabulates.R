set.seed(1)
n_row <- 2500L
n_col <- 800L
x <- matrix(sample.int(40L, n_row * n_col, replace = TRUE), nrow = n_row, ncol = n_col)
x[sample.int(length(x), 5000L)] <- NA_integer_
writeBin(as.integer(x), "/tmp/rowtabulates-seed1.bin")
one <- function() matrixStats::colTabulates(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
