suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

start <- c(0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0)
stop <- c(3, 3, 3, 4, 5, 5, 6, 1, 2, 2, 4, 4, 4, 6)
event <- c(1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0)
x1 <- c(0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1)
x2 <- c(1.2, -0.4, 0.5, 2.0, -1.1, 0.8, 0.3, -0.7, 1.5, 0.2, -1.4, 0.6, 1.1, -0.2)
strata <- c(1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2)
offset <- c(0, 0.1, 0, -0.2, 0.05, 0, 0, 0, -0.15, 0.2, 0, 0.05, 0, -0.1)
init <- c(0.2, -0.3)

time2 <- c(5, 4, 8, 2, 9, 6, 3, 7)
status2 <- c(1, 1, 0, 1, 1, 0, 1, 1)
x2a <- c(1.2, 0.4, 2.1, -0.3, 0.8, 1.5, -1.2, 0.1)
x2b <- c(0, 1, 0, 1, 1, 0, 1, 0)

control <- coxph.control(iter.max = 20, eps = 1e-9, toler.chol = 1e-12)

flat <- function(fit) {
  c(
    sprintf("%.17g", fit$coefficients),
    sprintf("%.17g", as.vector(fit$var)),
    sprintf("%.17g", fit$loglik),
    sprintf("%.17g", fit$score),
    sprintf("%.17g", fit$iter),
    sprintf("%.17g", fit$means),
    sprintf("%.17g", fit$residuals),
    sprintf("%.17g", as.vector(fit$linear.predictors))
  )
}

one <- function() {
  fit1 <- suppressWarnings(agexact.fit(
    cbind(x1, x2), cbind(start, stop, event), strata, offset, init, control,
    NULL, "exact", NULL, TRUE, c(0, 1)
  ))
  fit2 <- suppressWarnings(agexact.fit(
    cbind(x2a, x2b), cbind(time2, status2), NULL, NULL, NULL, control,
    NULL, "exact", NULL, TRUE, NULL
  ))
  c(flat(fit1), flat(fit2))
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
