.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Structure 3: pdDiag. Two random effects per Seed (Asym and R0 intercepts)
# with a diagonal covariance.
one <- function() {
  fm <- nlme(
    height ~ SSasymp(age, Asym, R0, lrc),
    data = Loblolly,
    fixed = Asym + R0 + lrc ~ 1,
    random = pdDiag(Asym + R0 ~ 1),
    start = c(Asym = 103, R0 = -8.5, lrc = -3.3)
  )
  # The stored pdMat is the random covariance divided by sigma^2.
  v <- fm$sigma^2 * pdMatrix(fm$modelStruct$reStruct)$Seed
  c(fixef(fm), v[1, 1], v[1, 2], v[2, 2], fm$sigma,
    as.numeric(logLik(fm)), fm$numIter)
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
