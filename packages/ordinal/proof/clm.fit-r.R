.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

data(wine)
y <- wine$rating
X <- model.matrix(~ contact + temp, data = wine)

one <- function() {
  fit <- clm.fit(y = y, X = X)
  c(fit$coefficients, fit$logLik, fit$edf, fit$nobs, fit$maxGradient,
    fit$niter, fit$convergence$code, fit$cond.H,
    as.vector(fit$vcov), as.vector(fit$gradient), as.vector(fit$Theta))
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
  paste(ifelse(is.na(value), "null", sprintf("%.17g", value)), collapse = ","),
  median(elapsed) * 1000
))
