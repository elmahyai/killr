.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

one <- function() {
  n <- 2000L
  i <- seq_len(n)
  x <- cbind(
    sin(i / 3) + 0.2 * cos(i),
    cos(i / 5) + 0.01 * i,
    rep(2, n)
  )
  y <- cbind(
    sin(i / 4) + 0.15 * cos(i / 2),
    cos(i / 6) + 0.005 * i,
    rep(1, n)
  )
  v <- sin(i / 7)
  list(
    nvar(mcmc(x)),
    nvar(mcmc(v)),
    nvar(mcmc.list(mcmc(x), mcmc(y))),
    nvar(1)
  )
}

fmt <- function(v) {
  if (is.null(v)) "null" else sprintf("%.17g", v)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, fmt, character(1))
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = "proof/nvar-r.txt")
shown <- vapply(value, function(v) if (is.null(v)) "NULL" else sprintf("%.17g", v), character(1))
writeLines(paste(shown, collapse = " "), con = "docs/output/nvar-r.txt")
