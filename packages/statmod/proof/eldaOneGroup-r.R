suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

collect <- function(out) {
  if (is.null(out$p)) {
    return(
      c(
        out$CI.frequency,
        out$deviance,
        out$dloglik.logdose,
        out$FisherInfo.logdose,
        out$dloglik.dose,
        out$FisherInfo.dose
      )
    )
  }
  c(
    out$p,
    out$lambda,
    out$alpha,
    out$CI.alpha,
    out$CI.frequency,
    out$deviance,
    out$iter,
    out$z.scoretest,
    out$z.scoretest.dose,
    out$dloglik.logdose,
    out$FisherInfo.logdose,
    out$dloglik.dose,
    out$FisherInfo.dose
  )
}

one <- function() {
  dose <- c(50, 100, 200, 400, 800)
  responses <- c(2, 6, 9, 15, 21)
  tested <- c(24, 24, 24, 24, 24)
  c(
    collect(eldaOneGroup(responses, dose, tested)),
    collect(eldaOneGroup(c(0, 0, 0, 0), c(50, 100, 200, 400), c(10, 10, 10, 10))),
    collect(eldaOneGroup(c(10, 10, 10, 10), c(50, 100, 200, 400), c(10, 10, 10, 10))),
    collect(eldaOneGroup(responses, dose, tested, observed = TRUE))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
