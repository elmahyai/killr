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
  chain <- mcmc(x)
  as.numeric(c(
    is.mcmc.list(mcmc.list(chain, mcmc(y))),
    is.mcmc.list(chain),
    is.mcmc.list(list(chain)),
    is.mcmc.list(NULL)
  ))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = "proof/is.mcmc.list-r.txt")
writeLines(
  paste(ifelse(value == 1, "TRUE", "FALSE"), collapse = " "),
  con = "docs/output/is.mcmc.list-r.txt"
)
