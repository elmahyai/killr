dir.create("/tmp/ms-rowquantiles-check", showWarnings = FALSE, recursive = TRUE)
set.seed(1)
x <- matrix(rnorm(200 * 80), nrow = 200, ncol = 80)
x[1, 1] <- NA
probs <- c(0.25, 0.75)
one <- function() {
  list(
    matrixStats::colQuantiles(x, probs = probs, na.rm = FALSE),
    matrixStats::colQuantiles(x, probs = probs, na.rm = TRUE)
  )
}
ans <- one()
writeBin(as.numeric(ans[[1]]), "/tmp/ms-rowquantiles-check/colQuantiles-false.bin")
writeBin(as.numeric(ans[[2]]), "/tmp/ms-rowquantiles-check/colQuantiles-true.bin")
cat(nrow(ans[[1]]), ncol(ans[[1]]), "\n", file = "/tmp/ms-rowquantiles-check/colQuantiles-shape.txt")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(median(elapsed), "\n")
