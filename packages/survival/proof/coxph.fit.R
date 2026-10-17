suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

one <- function() {
  d <- lung
  d$status <- d$status - 1
  d$ph_ecog <- d$ph.ecog
  d <- d[complete.cases(d[, c("time", "status", "age", "sex", "ph_ecog", "inst")]), ]
  x <- as.matrix(d[, c("age", "sex", "ph_ecog")])
  y <- cbind(d$time, d$status)
  fit <- coxph.fit(x, y, d$inst, NULL, NULL, coxph.control(), NULL, "efron",
                   rownames(d), TRUE, c(-1, 0, 1))
  vals <- c(as.numeric(fit$coefficients), as.numeric(fit$var),
            as.numeric(fit$loglik), fit$score, as.numeric(fit$means),
            as.numeric(fit$residuals), as.numeric(fit$linear.predictors))
  sprintf("%.17g", vals)
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
