.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

# Direct Csurvreg6 calls. Three fits: extreme value with weights and an offset,
# Gaussian with a fixed log-scale, and logistic interval censoring with two scales.
call6 <- function(maxiter, nvar, y, x, wt, offset, beta, nstrat, strata, dist, ny) {
  .Call(
    survival:::Csurvreg6,
    as.integer(maxiter),
    as.integer(nvar),
    as.double(y),
    as.integer(ny),
    as.double(x),
    as.double(wt),
    as.double(offset),
    as.double(beta),
    as.integer(nstrat),
    as.integer(strata),
    1e-9,
    1e-10,
    as.integer(dist),
    1,
    1
  )
}

pack <- function(fit) {
  c(fit$coef, fit$loglik, fit$u, fit$var, fit$iter, fit$flag)
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
beta_main <- c(3, 1, -1, -1)
strata_main <- rep(1L, n)

n2 <- 40
idx2 <- seq_len(n2)
time2 <- 20 + (idx2 %% 15)
status2 <- ifelse((idx2 %% 4) == 0, 2, 1)
y_g <- cbind(time2, status2)
x_g <- cbind(1, (idx2 %% 5) - 2)
beta_g <- c(25, 0.5, log(4))
strata_g <- rep(1L, n2)

n3 <- 36
idx3 <- seq_len(n3)
t1 <- 1 + (idx3 %% 8)
t2 <- t1 + 1 + (idx3 %% 3)
status3 <- ifelse((idx3 %% 3) == 0, 3, ifelse((idx3 %% 3) == 1, 1, 0))
y_l <- cbind(t1, t2, status3)
x_l <- cbind(1, ((idx3 %% 2) * 2) - 1)
strata_l <- ifelse(idx3 <= 18, 1L, 2L)
beta_l <- c(4, 0.3, log(1.5), log(2))

one <- function() {
  a <- call6(30, 3, y_main, x_main, wt_main, off_main, beta_main, 1, strata_main, 1, 2)
  b <- call6(30, 2, y_g, x_g, rep(1, n2), rep(0, n2), beta_g, 0, strata_g, 3, 2)
  cfit <- call6(30, 2, y_l, x_l, rep(1, n3), rep(0, n3), beta_l, 2, strata_l, 2, 3)
  c(pack(a), pack(b), pack(cfit))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"values":[%s],"median_ms":%.17g}\n',
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
