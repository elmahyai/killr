.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(minpack.lm))
stopifnot(packageVersion("minpack.lm") == "1.2.4")

Treated <- Puromycin[Puromycin$state == "treated", ]

.pack <- c(
  as.numeric(
    nlsLM(
      rate ~ Vm * conc / (K + conc),
      data = Treated,
      start = c(Vm = 200, K = 0.05),
      weights = wfct(1 / rate)
    )$weights
  ),
  as.numeric(
    nlsLM(
      rate ~ Vm * conc / (K + conc),
      data = Treated,
      start = c(Vm = 200, K = 0.05),
      weights = wfct(sqrt(conc))
    )$weights
  ),
  as.numeric(
    nlsLM(
      rate ~ Vm * conc / (K + conc),
      data = Treated,
      start = c(Vm = 200, K = 0.05),
      weights = wfct(1 / fitted^2)
    )$weights
  )
)

value <- .pack
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  .pack <- c(
    as.numeric(
      nlsLM(
        rate ~ Vm * conc / (K + conc),
        data = Treated,
        start = c(Vm = 200, K = 0.05),
        weights = wfct(1 / rate)
      )$weights
    ),
    as.numeric(
      nlsLM(
        rate ~ Vm * conc / (K + conc),
        data = Treated,
        start = c(Vm = 200, K = 0.05),
        weights = wfct(sqrt(conc))
      )$weights
    ),
    as.numeric(
      nlsLM(
        rate ~ Vm * conc / (K + conc),
        data = Treated,
        start = c(Vm = 200, K = 0.05),
        weights = wfct(1 / fitted^2)
      )$weights
    )
  )
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
