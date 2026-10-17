.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
d <- data.frame(
  y = c(5.2, 3.1, 8.4, 4.2, 6.7),
  x1 = c(1, 2, 3, 4, 5),
  x2 = c(0.5, 1, 0.8, 1, 1)
)
one <- function() {
  m <- lm(y ~ x1 + x2, data = d)
  r <- logtrans(m, alpha = seq(0.1, 2, length.out = 5), plotit = FALSE, interp = FALSE)
  c(r$x, r$y)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
