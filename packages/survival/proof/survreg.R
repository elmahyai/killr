.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

# Four survreg() calls on the same synthetic data: extreme value with weights
# and a missing covariate, a factor with an offset() term, a strata() term,
# and the Weibull alias (log-time transform, extreme value fit).
n <- 300
idx <- seq_len(n)
x1 <- ((idx * 17) %% 10) / 10
x1[idx %% 37 == 0] <- NA
x2 <- as.numeric((idx * 13) %% 7) - 3
g <- c("alpha", "beta", "gamma")[(idx %% 3) + 1]
time <- 0.3 + ((idx * 31) %% 50) / 10
status <- ifelse((idx %% 5) == 0, 0, 1)
off <- ((idx %% 4) - 1) * 0.05
wt <- 1 + (idx %% 3) * 0.5
df <- data.frame(time = time, status = status, x1 = x1, x2 = x2, g = g, off = off, wt = wt)

ctrl <- survreg.control()

pack <- function(fit) {
  na <- if (is.null(fit$na.action)) integer(0) else as.integer(fit$na.action)
  c(length(na), na,
    fit$coefficients, fit$icoef, fit$var, fit$loglik, fit$iter,
    fit$linear.predictors, fit$df.residual, fit$idf, fit$scale, fit$means,
    as.vector(fit$y))
}

one <- function() {
  a <- survreg(Surv(time, status) ~ x1 + x2, data = df, weights = wt, dist = "extreme", control = ctrl)
  b <- survreg(Surv(time, status) ~ g + x1 + offset(off), data = df, dist = "extreme", control = ctrl)
  cc <- survreg(Surv(time, status) ~ x2 + strata(g), data = df, dist = "extreme", control = ctrl)
  d <- survreg(Surv(time, status) ~ x2, data = df, dist = "weibull", control = ctrl)
  c(pack(a), pack(b), pack(cc), pack(d))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", value), collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
