.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
x <- matrix(
  c(
    2.4, 2.8, 0.5, 2.4, 0.3, 2.7, 0.7, 2.9, 0.8, 1.7,
    1.5, 1.3, 1.8, 2.0, 1.6, 1.4, 1.9, 2.2, 1.7, 1.1,
    0.3, 0.5, 0.4, 0.6, 0.2, 0.7, 0.1, 0.8, 0.3, 0.4
  ),
  ncol = 3
)
one <- function() {
  set.seed(123)
  fit <- cov.mve(x)
  c(
    as.numeric(fit$center),
    as.numeric(fit$cov),
    fit$crit,
    fit$n.obs
  )
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
