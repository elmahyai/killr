.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
data(denmark)
sjd <- as.matrix(denmark[, c("LRM", "LRY", "IBO", "IDE")])

one <- function() {
  sjd.vecm <- ca.jo(sjd, ecdet = "const", type = "eigen", K = 2, spec = "longrun", season = 4)
  z <- sjd.vecm
  r <- 1L
  idx <- r + 1
  df <- length(idx:z@P)
  N <- nrow(z@Z0)
  test1 <- ca.jo(z@x, ecdet = "const", K = z@lag, season = z@season, dumvar = z@dumvar)
  test2 <- ca.jo(z@x, ecdet = "none", K = z@lag, season = z@season, dumvar = z@dumvar)
  teststat <- -N * sum(log((1 - test1@lambda[idx:z@P]) / (1 - test2@lambda[idx:z@P])))
  pval <- 1 - pchisq(teststat, df)
  c(teststat, pval)
}

time_one <- function() {
  sjd.vecm <- ca.jo(sjd, ecdet = "const", type = "eigen", K = 2, spec = "longrun", season = 4)
  capture.output(lttest(sjd.vecm, r = 1))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  time_one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
