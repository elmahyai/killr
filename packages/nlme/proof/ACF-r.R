.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  fm1 <- lme(
    follicles ~ sin(2 * pi * Time) + cos(2 * pi * Time),
    Ovary,
    random = ~ sin(2 * pi * Time) | Mare
  )
  out <- ACF(fm1, maxLag = 11)
  c(out$lag, out$ACF)
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
