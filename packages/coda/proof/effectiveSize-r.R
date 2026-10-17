.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

n <- 2000L
i <- seq_len(n)
x <- cbind(sin(i / 3) + 0.2 * cos(i), cos(i / 5) + 0.01 * i, rep(2, n))
y <- cbind(sin(i / 4) + 0.15 * cos(i / 2), cos(i / 6) + 0.005 * i, rep(1, n))

one <- function() {
  as.numeric(effectiveSize(mcmc.list(mcmc(x), mcmc(y))))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
