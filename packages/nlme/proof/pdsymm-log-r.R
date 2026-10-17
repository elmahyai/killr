.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

# R's matrixLog_pd (nlme src/pdMat.c, called by pdFactor.pdSymm) through the
# registered native routine. Cases are the same LCG stream the Python proof uses.
matrix_log_routine <- getDLLRegisteredRoutines("nlme")$.C$matrixLog_pd

# Parameter order for each case: 8 random positive definite cases (uniform
# half-log entries in [-0.7, 0.7]), then 4 near-singular cases where the (1,1)
# half-log entry is shifted by -4, -6, -8, -10.
case_orders <- c(2, 3, 4, 5, 6, 3, 4, 2, 3, 4, 5, 6)
shifts <- c(0, 0, 0, 0, 0, 0, 0, 0, 4, 6, 8, 10)

state <- 12345
lcg_uniform <- function() {
  state <<- (1664525 * state + 1013904223) %% 4294967296
  state / 4294967296
}

cases <- vector("list", length(case_orders))
for (k in seq_along(case_orders)) {
  q <- case_orders[[k]]
  n_par <- q * (q + 1) / 2
  params <- vapply(seq_len(n_par), function(i) (2 * lcg_uniform() - 1) * 0.7, numeric(1))
  params[[1]] <- params[[1]] - shifts[[k]]
  cases[[k]] <- list(q = q, params = params)
}

one <- function() {
  out <- numeric(0)
  for (cs in cases) {
    q <- cs$q
    factor <- .C(matrix_log_routine, Factor = double(q * q), as.integer(q), as.double(cs$params))$Factor
    L <- matrix(factor, q, q)
    value <- crossprod(L)
    out <- c(out, factor, as.vector(value))
  }
  out
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
