.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed input: the Oats gls fit with corAR1(form = ~ 1 | Block), so apVar is a
## matrix. The fit runs in the untimed setup; only intervals() is timed.
data(Oats, package = "nlme")
fm <- gls(yield ~ Variety - 1, Oats, correlation = corAR1(form = ~ 1 | Block))

one <- function() {
  a <- intervals(fm, level = 0.95, which = "all")
  c(as.numeric(a$coef), as.numeric(a$corStruct), as.numeric(a$sigma))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
