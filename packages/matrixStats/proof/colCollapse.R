x <- matrix(as.numeric(seq_len(400 * 250)), nrow = 400, ncol = 250)
idxs <- rep(seq_len(400), length.out = 250)
one <- function() matrixStats::colCollapse(x, idxs)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
