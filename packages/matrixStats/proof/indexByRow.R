# Time matrixStats::indexByRow. One untimed call, then the median of 20.
# Sys.time() differences are reported in milliseconds.
# The timed call is dim = c(500, 400), idxs NULL.
# A short idxs vector and a negative idxs vector are checked outside the timer.
library(matrixStats)

dim <- c(500L, 400L)

one <- function() indexByRow(dim)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
y <- one()
writeBin(y, "/tmp/indexByRow-timed.bin")

short <- indexByRow(dim, idxs = c(1L, 7L, 400L, 200000L))
negative <- tryCatch(
  indexByRow(dim, idxs = c(-1L, -2L)),
  error = function(e) conditionMessage(e)
)

cat(sprintf("%.17g\n", median(elapsed) * 1000))
cat(paste(sprintf("%d", short), collapse = " "), "\n", sep = "")
cat(negative, "\n", sep = "")
cat(length(y), "\n", sep = "")
cat(sprintf("%d %d\n", y[1], y[length(y)]))
