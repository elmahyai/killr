# Timing proof for matrixStats::binCounts. One untimed call, then the median of 20.
# R time is Sys.time(), in milliseconds.
library(matrixStats)

set.seed(1)
x <- runif(100000, 0, 10)
bx <- 0:10
boundary <- c(0, 1, 2, 5, 10)

one <- function() {
  list(
    right_true = binCounts(x, bx = bx, right = TRUE),
    right_false = binCounts(x, bx = bx, right = FALSE),
    boundary_true = binCounts(boundary, bx = bx, right = TRUE),
    boundary_false = binCounts(boundary, bx = bx, right = FALSE)
  )
}

warm <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf("%.17g", median(elapsed) * 1000), "\n", sep = "")
cat(paste(warm$right_true, collapse = " "), "\n", sep = "")
cat(paste(warm$right_false, collapse = " "), "\n", sep = "")
cat(paste(warm$boundary_true, collapse = " "), "\n", sep = "")
cat(paste(warm$boundary_false, collapse = " "), "\n", sep = "")
writeBin(x, "/tmp/killr-bincounts-x.bin")
