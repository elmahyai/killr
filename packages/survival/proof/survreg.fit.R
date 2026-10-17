.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

# Three survreg.fit calls: extreme value with weights and an offset, Gaussian
# with a fixed log-scale, and logistic interval censoring with two scales.
ctrl <- survreg.control()

pack <- function(fit) {
  c(fit$coefficients, fit$icoef, fit$var, fit$loglik, fit$iter,
    fit$linear.predictors, fit$df, fit$score)
}

n <- 2000
idx <- seq_len(n)
x1 <- ((idx * 17) %% 10) / 10
x2 <- as.numeric((idx * 13) %% 7) - 3
time <- 0.3 + ((idx * 31) %% 50) / 10
status <- ifelse((idx %% 5) == 0, 0, 1)
y_main <- cbind(log(time), status)
x_main <- cbind(1, x1, x2)
wt_main <- 1 + (idx %% 3) * 0.5
off_main <- ((idx %% 4) - 1) * 0.05
strata_main <- rep(1L, n)

n2 <- 40
idx2 <- seq_len(n2)
time2 <- 20 + (idx2 %% 15)
status2 <- ifelse((idx2 %% 4) == 0, 2, 1)
y_g <- cbind(time2, status2)
x_g <- cbind(1, (idx2 %% 5) - 2)

n3 <- 36
idx3 <- seq_len(n3)
t1 <- 1 + (idx3 %% 8)
t2 <- t1 + 1 + (idx3 %% 3)
status3 <- ifelse((idx3 %% 3) == 0, 3, ifelse((idx3 %% 3) == 1, 1, 0))
y_l <- cbind(t1, t2, status3)
x_l <- cbind(1, ((idx3 %% 2) * 2) - 1)
strata_l <- ifelse(idx3 <= 18, 1L, 2L)

one <- function() {
  a <- survival:::survreg.fit(
    x_main, y_main, weights = wt_main, offset = off_main, init = NULL,
    controlvals = ctrl, dist = "extreme", scale = 0, nstrat = 1,
    strata = strata_main
  )
  b <- survival:::survreg.fit(
    x_g, y_g, weights = NULL, offset = NULL, init = NULL,
    controlvals = ctrl, dist = "gaussian", scale = 4, nstrat = 1
  )
  cc <- survival:::survreg.fit(
    x_l, y_l, weights = NULL, offset = NULL, init = NULL,
    controlvals = ctrl, dist = "logistic", scale = 0, nstrat = 2,
    strata = strata_l
  )
  c(pack(a), pack(b), pack(cc))
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
