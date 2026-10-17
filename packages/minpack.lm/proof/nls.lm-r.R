.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(minpack.lm))
stopifnot(packageVersion("minpack.lm") == "1.2.4")

fn <- function(p) c(1 - p[1], 10 * (p[2] - p[1]^2))
jac <- function(p) c(-1, -20 * p[1], 0, 10)
fn_list <- function(p) c(1 - p$a, 10 * (p$b - p$a^2))

pack <- function(fit) {
  diag_is_list <- is.list(fit$diag)
  c(
    as.numeric(unlist(fit$par)),
    as.numeric(fit$hessian),
    as.numeric(fit$fvec),
    as.numeric(fit$info),
    as.numeric(fit$niter),
    as.numeric(fit$deviance),
    as.numeric(diag_is_list),
    as.numeric(unlist(fit$diag)),
    as.numeric(fit$rsstrace[seq_len(fit$niter)])
  )
}

one <- function() {
  finite <- nls.lm(par = c(-1.2, 1), fn = fn)
  analytic <- nls.lm(par = c(-1.2, 1), fn = fn, jac = jac)
  bounded <- nls.lm(
    par = c(1, 1), fn = fn,
    lower = c(0, 0), upper = c(0.5, 2)
  )
  stopped <- nls.lm(
    par = c(-1.2, 1), fn = fn,
    control = nls.lm.control(maxiter = 2)
  )
  scaled <- nls.lm(
    par = c(-1.2, 1), fn = fn,
    control = nls.lm.control(diag = c(1, 2))
  )
  named <- nls.lm(par = list(a = -1.2, b = 1), fn = fn_list)
  stopifnot(finite$message == "Relative error between `par' and the solution is at most `ptol'.")
  stopifnot(grepl("gtol", analytic$message, fixed = TRUE))
  stopifnot(stopped$info == -1L)
  stopifnot(grepl("maxiter", stopped$message, fixed = TRUE))
  c(
    pack(finite),
    pack(analytic),
    pack(bounded),
    pack(stopped),
    pack(scaled),
    pack(named)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
