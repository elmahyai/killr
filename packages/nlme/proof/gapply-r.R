.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(Orthodont, package = "nlme")

one <- function() {
  m1 <- gapply(Orthodont, FUN = function(x) mean(x$distance), form = distance ~ age | Subject)
  m2 <- gapply(Orthodont, which = c(1, 2), FUN = function(x) nrow(x) + mean(x$age))
  m3 <- gapply(Orthodont, which = "distance", FUN = function(x) max(x$distance) - min(x$distance),
               form = distance ~ age | Subject)
  c(as.vector(m1), as.vector(m2), as.vector(m3))
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
