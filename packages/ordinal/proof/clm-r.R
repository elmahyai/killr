.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

data(wine)

pack <- function(fit) {
  th <- fit$Theta
  if (is.data.frame(th)) th <- th[, vapply(th, is.numeric, logical(1)), drop = FALSE]
  c(fit$coefficients, fit$logLik, fit$edf, fit$nobs, fit$maxGradient,
    fit$niter, fit$convergence$code, fit$cond.H,
    as.vector(fit$vcov), as.vector(fit$gradient), as.vector(as.matrix(th)))
}

one <- function() {
  c(pack(clm(rating ~ contact + temp, data = wine)),
    pack(clm(rating ~ contact, scale = ~ temp, data = wine)),
    pack(clm(rating ~ temp, nominal = ~ contact, data = wine)))
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
