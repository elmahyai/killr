suppressPackageStartupMessages(library(isoband))

# Fixed angles: a scalar angle, a recycled vector angle, and an empty x.
make_cases <- function() {
  n <- 2000
  x <- -1 + 2 * (0:(n - 1)) / (n - 1)
  list(
    list(name = "scalar", theta = 0.7, x = x),
    list(name = "recycled", theta = c(0.1, 0.2, 0.3), x = x[1:1001]),
    list(name = "empty", theta = -1.5, x = numeric(0))
  )
}

run_all <- function(cases) {
  lapply(cases, function(cs) angle_fixed(cs$theta)(cs$x))
}

emit_vec <- function(case, name, v) {
  n <- length(v)
  cat(sprintf("L\t%s\t%s\t%d\n", case, name, n), sep = "")
  if (n > 0) cat(sprintf("V\t%s\t%s\t%d\t%.17g\n", case, name, seq_len(n), as.double(v)), sep = "")
}

emit <- function(res, cases) {
  for (k in seq_along(cases)) emit_vec(cases[[k]]$name, "out", res[[k]])
}

cases <- make_cases()
timing_cases <- rep(cases, 200)
res <- run_all(cases) # untimed call
times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(run_all(timing_cases))
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(times) * 1000))
emit(res, cases)
