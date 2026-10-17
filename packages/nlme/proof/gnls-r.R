.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
stopifnot(packageDescription("nlme")$Version == "3.1-171")

x <- c(0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8)
y <- c(2.71, 2.35, 2.08, 1.84, 1.63, 1.45, 1.29, 1.16, 1.04, 0.93, 0.84, 0.76, 0.69, 0.63, 0.57, 0.52)

one <- function() {
  fit <- gnls(
    y ~ a * exp(b * x),
    data = data.frame(x = x, y = y),
    start = c(a = 2, b = -0.15),
    control = gnlsControl(apVar = FALSE)
  )
  c(
    coef(fit),
    fit$sigma,
    fit$logLik,
    fit$numIter,
    as.numeric(fitted(fit)),
    as.numeric(residuals(fit)),
    as.numeric(fit$varBeta)
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
