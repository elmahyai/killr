.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

one <- function() {
  ctrl <- clm.control()
  c(match(ctrl$method, c("Newton", "model.frame", "design", "ucminf", "nlminb", "optim")),
    match(ctrl$sign.location, c("negative", "positive")),
    match(ctrl$sign.nominal, c("positive", "negative")),
    match(ctrl$convergence, c("warn", "silent", "stop", "message")),
    ctrl$trace, ctrl$maxIter, ctrl$gradTol, ctrl$relTol, ctrl$tol,
    ctrl$maxLineIter, ctrl$maxModIter)
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
