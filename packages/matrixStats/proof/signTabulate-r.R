library(matrixStats)

set.seed(1)
x <- rnorm(100000)
x[c(1, 10, 100, 1000, 10000)] <- 0
x[c(2, 20, 200)] <- NA
x[3] <- Inf
x[4] <- -Inf
x[5] <- NaN

double_small <- as.numeric(unname(signTabulate(c(-2, -Inf, 0, 1, Inf, NA, NaN))))
integer_small <- as.numeric(unname(signTabulate(c(-2L, -1L, 0L, 1L, NA_integer_, 5L))))

one <- function() matrixStats::signTabulate(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
timed <- as.numeric(unname(one()))

fmt <- function(v) paste(sprintf("%.0f", v), collapse = ",")
cat(sprintf(
  "{\"double_small\":[%s],\"integer_small\":[%s],\"timed\":[%s],\"median_ms\":%.17g}\n",
  fmt(double_small),
  fmt(integer_small),
  fmt(timed),
  median(elapsed) * 1000
))
