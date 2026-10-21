.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

data(wine)

one <- function() {
  fm1 <- clmm(rating ~ contact + temp + (1|judge), data = wine)
  vc <- VarCorr(fm1)
  c(as.numeric(unlist(lapply(vc, as.matrix))),
    as.numeric(unlist(lapply(vc, attr, "stddev"))))
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
