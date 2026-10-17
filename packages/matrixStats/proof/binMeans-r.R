# Timing proof for matrixStats::binMeans. One untimed call, then the median of 20.
# R time is Sys.time(), in milliseconds.
library(matrixStats)

set.seed(1)
x <- runif(100000, 0, 10)
y <- runif(100000, 0, 10)
bx <- 0:10
boundary_x <- c(0, 1, 2, 5, 10)
boundary_y <- c(10, 20, 30, 40, 50)

fmt <- function(values) {
  paste(ifelse(is.na(values), "NA", sprintf("%.17g", values)), collapse = " ")
}

one <- function() {
  list(
    right_true = binMeans(y, x = x, bx = bx, right = TRUE),
    right_false = binMeans(y, x = x, bx = bx, right = FALSE),
    boundary_true = binMeans(boundary_y, x = boundary_x, bx = bx, right = TRUE),
    boundary_false = binMeans(boundary_y, x = boundary_x, bx = bx, right = FALSE)
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
for (item in warm) {
  cat(fmt(item), "\n", sep = "")
  cat(paste(attr(item, "count"), collapse = " "), "\n", sep = "")
}
writeBin(x, "/tmp/killr-binmeans-x.bin")
writeBin(y, "/tmp/killr-binmeans-y.bin")
