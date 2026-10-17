.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

data(Orthodont, package = "nlme")

one <- function() {
  fm1 <- lmList(Orthodont)
  fm2 <- lmList(distance ~ age | Subject, Orthodont)
  c(as.numeric(unlist(coef(fm1))), as.numeric(unlist(coef(fm2))))
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
