.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(Orthodont, package = "nlme")
fm1 <- lmList(Orthodont)
fm2 <- lme(fm1)

one <- function() {
  cp <- comparePred(fm1, fm2, length.out = 2)
  grp <- cp[[2]]
  c(
    as.numeric(cp[[1]]),
    as.numeric(factor(grp, levels = levels(grp))),
    as.numeric(cp[[3]]),
    as.numeric(cp$.type)
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
