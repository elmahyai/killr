suppressPackageStartupMessages(library(survival))

one <- function() {
  fit <- coxph(Surv(futime, fustat) ~ age + rx + ecog.ps, ovarian, x = TRUE, model = TRUE)
  fitd <- coxph.detail(fit)
  c(
    sprintf("%.17g", sum(fitd$time)),
    sprintf("%.17g", sum(fitd$nevent)),
    sprintf("%.17g", sum(fitd$nrisk)),
    sprintf("%.17g", sum(fitd$means)),
    sprintf("%.17g", sum(fitd$score)),
    sprintf("%.17g", sum(fitd$imat)),
    sprintf("%.17g", sum(fitd$hazard)),
    sprintf("%.17g", sum(fitd$varhaz)),
    sprintf("%.17g", sum(fitd$wtrisk))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
