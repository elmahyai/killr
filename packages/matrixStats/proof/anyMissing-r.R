set.seed(1)
x <- rnorm(100000)
x[seq(100, length(x), by = 100)] <- NA

no_na <- matrixStats::anyMissing(c(1, 2, 3, 4))
has_na <- matrixStats::anyMissing(c(1, NA, 3))
idxs <- matrixStats::anyMissing(c(1, NA, 3, 4), idxs = c(1, 3, 4))
listed <- matrixStats::anyMissing(list(c(1, 2), c(4, NA)))

one <- function() matrixStats::anyMissing(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"no_na\":%s,\"has_na\":%s,\"idxs\":%s,\"listed\":%s,\"timed\":%s,\"median_ms\":%.17g}\n",
  ifelse(no_na, "true", "false"),
  ifelse(has_na, "true", "false"),
  ifelse(idxs, "true", "false"),
  ifelse(listed, "true", "false"),
  ifelse(one(), "true", "false"),
  median(elapsed) * 1000
))
