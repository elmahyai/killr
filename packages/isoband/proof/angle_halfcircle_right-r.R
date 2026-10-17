suppressPackageStartupMessages(library(isoband))

# Angles on a grid from -3pi to 3pi, with the edge values first, and a wide sweep.
make_cases <- function() {
  n <- 2000
  grid <- -3 * pi + 6 * pi * (0:(n - 1)) / (n - 1)
  edges <- c(-pi / 2, pi / 2, 0, pi, -pi, 3 * pi / 2, -3 * pi / 2)
  m <- 1000
  wide <- -10 + 20 * (0:(m - 1)) / (m - 1)
  list(
    list(name = "grid_edges", theta = c(edges, grid)),
    list(name = "wide", theta = wide)
  )
}

run_all <- function(cases) {
  lapply(cases, function(cs) angle_halfcircle_right()(cs$theta))
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
