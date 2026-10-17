.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

n <- 800L
i <- seq_len(n)
x <- cbind(sin(i / 3) + 0.2 * cos(i), cos(i / 5) + 0.01 * i, rep(2, n))

one <- function() {
  out <- spectrum0.ar(x)
  c(as.numeric(out$spec), as.numeric(out$order))
}

value <- one()
elapsed <- numeric(20)
for (j in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[j]] <- as.numeric(Sys.time()) - t0
}
spec <- value[1:3]
ord <- value[4:6]
parts_spec <- vapply(spec, sprintf, fmt = "%.17g", character(1))
parts_ord <- vapply(ord, sprintf, fmt = "%.17g", character(1))
cat(sprintf(
  "{\"spec\":[%s],\"order\":[%s],\"median_ms\":%.17g}\n",
  paste(parts_spec, collapse = ","),
  paste(parts_ord, collapse = ","),
  median(elapsed) * 1000
))
