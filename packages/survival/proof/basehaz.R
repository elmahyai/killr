suppressPackageStartupMessages(library(survival))

fit <- coxph(Surv(time, status) ~ 1, data = lung)

one <- function() {
  bh <- basehaz(fit)
  c(sprintf("%.17g", bh$hazard), sprintf("%.17g", bh$time))
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
