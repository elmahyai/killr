.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(Orthodont, package = "nlme")

one <- function() {
  o2 <- Orthodont[-1, ]
  c(
    as.numeric(isBalanced(Orthodont)),
    as.numeric(isBalanced(Orthodont, countOnly = TRUE)),
    as.numeric(isBalanced(o2)),
    as.numeric(isBalanced(o2, countOnly = TRUE))
  )
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
