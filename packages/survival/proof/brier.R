suppressPackageStartupMessages(library(survival))

one <- function() {
  data(rotterdam, package = "survival")
  cfit <- coxph(
    Surv(rtime, recur) ~ age + meno + size + pmin(nodes, 11),
    data = rotterdam,
    x = TRUE,
    model = TRUE
  )
  br <- brier(cfit, times = c(4, 6) * 365.25)
  c(
    sprintf("%.17g", br$rsquared),
    sprintf("%.17g", br$brier),
    sprintf("%.17g", br$times)
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
