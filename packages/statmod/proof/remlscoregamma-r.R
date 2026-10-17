suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

collect <- function(out) {
  c(
    out$beta,
    out$se.beta,
    out$gamma,
    out$se.gam,
    out$mu,
    out$phi,
    out$deviance,
    out$h
  )
}

one <- function() {
  data(welding)
  y <- welding$Strength
  X <- cbind(1, (welding$Drying + 1) / 2, (welding$Material + 1) / 2)
  Z <- cbind(
    1,
    (welding$Material + 1) / 2,
    (welding$Method + 1) / 2,
    (welding$Preheating + 1) / 2
  )
  collect(remlscoregamma(y, X, Z))
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
