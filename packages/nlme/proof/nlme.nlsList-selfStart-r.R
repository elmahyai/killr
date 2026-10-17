.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}
suppressPackageStartupMessages(library(nlme))

one <- function() {
  fit <- nlsList(height ~ SSasympOff(age, Asym, lrc, c0) | Seed, data = Loblolly)
  fm <- nlme(fit, random = Asym ~ 1)
  re <- as.matrix(ranef(fm))
  re <- re[order(rownames(re)), , drop = FALSE]
  c(fixef(fm), fm$sigma, as.numeric(logLik(fm)), as.vector(re))
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
