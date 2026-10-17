.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))

one <- function() {
  pts <- matrix(c(1, 2, 2, 3, 5, 1, 4, 2, 3, 5), 5, 2, byrow = TRUE)
  d <- dist(pts)
  y0 <- matrix(
    c(-0.5, 0.2, 0.1, -0.3, 0.4, 0.3, -0.1, 0.5, -0.2, 0),
    5,
    2,
    byrow = TRUE
  )
  res <- isoMDS(d, y = y0, trace = FALSE, maxit = 50)
  sh <- Shepard(d, res$points)
  c(sh$x, sh$y, sh$yf)
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
