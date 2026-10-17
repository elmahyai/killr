.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

data(wine)

## Default start: clm.fit thresholds and location effects, then 0 for the random-effect sd.

pack <- function(fit) {
  c(fit$coefficients, fit$logLik, as.vector(unlist(fit$ST)),
    as.vector(fit$ranef), as.vector(fit$condVar), as.vector(fit$gradient),
    as.vector(fit$Hessian))
}

one <- function() {
  pack(clmm(rating ~ contact + temp + (1 | judge), data = wine))
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
