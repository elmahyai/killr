.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

one <- function() {
  ctrl <- clmm2.control()
  c(match(ctrl$method, c("ucminf", "nlminb", "model.frame")),
    ctrl$ctrl$trace, ctrl$ctrl$maxIter, ctrl$ctrl$gradTol, ctrl$ctrl$maxLineIter,
    match(ctrl$ctrl$innerCtrl, c("warnOnly", "noWarn", "giveError")),
    ctrl$optCtrl$trace, ctrl$optCtrl$grtol,
    match(ctrl$optCtrl$grad, c("central", "forward")))
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
