.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(minpack.lm))
stopifnot(packageVersion("minpack.lm") == "1.2.4")

Treated <- Puromycin[Puromycin$state == "treated", ]
x <- 1:10
y <- 2 * x + 3

pack_fit <- function(fit) {
  w <- if (is.null(fit$weights)) numeric(0) else as.numeric(fit$weights)
  c(
    as.numeric(coef(fit)),
    as.numeric(residuals(fit)),
    as.numeric(fitted(fit)),
    as.numeric(deviance(fit)),
    as.numeric(fit$convInfo$isConv),
    as.numeric(fit$convInfo$finIter),
    as.numeric(fit$convInfo$finTol),
    as.numeric(fit$convInfo$stopCode),
    as.numeric(length(w)),
    w
  )
}

one <- function() {
  plain <- nlsLM(
    rate ~ Vm * conc / (K + conc),
    data = Treated,
    start = c(Vm = 200, K = 0.05)
  )
  weighted <- nlsLM(
    rate ~ Vm * conc / (K + conc),
    data = Treated,
    start = c(Vm = 200, K = 0.05),
    weights = 1 / rate
  )
  linear <- nlsLM(y ~ a + b * x, start = list(a = 0.12345, b = 0.54321))
  part <- nlsLM(
    y ~ a + b * x,
    start = list(a = 0.12345, b = 0.54321),
    subset = 1:5
  )
  stopifnot(plain$convInfo$isConv)
  stopifnot(plain$convInfo$stopMessage == "Relative error in the sum of squares is at most `ftol'.")
  c(pack_fit(plain), pack_fit(weighted), pack_fit(linear), pack_fit(part))
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
