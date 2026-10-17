.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

one <- function() {
  n <- 2000L
  i <- seq_len(n)
  x1 <- cbind(sin(i / 3) + 0.2 * cos(i), cos(i / 5) + 0.01 * i)
  x2 <- cbind(sin(i / 4) + 0.15 * cos(i / 2), cos(i / 6) + 0.005 * i)
  ml <- mcmc.list(mcmc(x1), mcmc(x2))
  g <- gelman.diag(ml, autoburnin = FALSE)
  c(as.numeric(g$psrf), as.numeric(g$mpsrf))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(
  value,
  function(v) if (is.na(v)) "null" else sprintf("%.17g", v),
  character(1)
)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "gelman.diag-r.txt"))
