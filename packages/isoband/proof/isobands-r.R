suppressPackageStartupMessages(library(isoband))

# Fixed grids: smooth values, and integer-valued values with NA cells.
make_cases <- function() {
  sizes <- list(c(5, 7), c(20, 30), c(60, 80), c(150, 120))
  cases <- list()
  for (s in sizes) {
    nr <- s[1]
    nc <- s[2]
    x <- (0:(nc - 1)) / (nc - 1)
    y <- (0:(nr - 1)) / (nr - 1) * 1.5
    z_smooth <- matrix(0, nr, nc)
    z_int <- matrix(0, nr, nc)
    for (r in 0:(nr - 1)) {
      for (k in 0:(nc - 1)) {
        z_smooth[r + 1, k + 1] <- sin(3 * x[k + 1]) * cos(2 * y[r + 1]) + 0.5 * x[k + 1] * y[r + 1]
        v <- ((7 * r + 13 * k + 3 * r * k) %% 11) / 10
        if ((r + 2 * k) %% 9 == 0) v <- NA_real_
        z_int[r + 1, k + 1] <- v
      }
    }
    # the smooth pair 0.8:0.3 is given high-below-low on purpose, to test the swap
    cases[[length(cases) + 1]] <- list(
      name = sprintf("smooth_%dx%d", nr, nc), x = x, y = y, z = z_smooth,
      low = c(-0.4, 0, 0.8, 0.5), high = c(0, 0.3, 0.3, 1.2)
    )
    cases[[length(cases) + 1]] <- list(
      name = sprintf("int_%dx%d", nr, nc), x = x, y = y, z = z_int,
      low = c(0, 0.25, 0.5), high = c(0.25, 0.5, 1.0)
    )
  }
  cases
}

run_all <- function(cases) {
  lapply(cases, function(cs) unclass(isobands(cs$x, cs$y, cs$z, cs$low, cs$high)))
}

emit <- function(res, cases) {
  for (k in seq_along(res)) {
    nm <- cases[[k]]$name
    for (g in seq_along(res[[k]])) {
      cat(sprintf("G\t%s\t%d\n", nm, g))
      el <- res[[k]][[g]]
      if (length(el$x) > 0) {
        cat(sprintf("P\t%s\t%d\t%.17g\t%.17g\t%d\n", nm, g, el$x, el$y, as.integer(el$id)), sep = "")
      }
    }
  }
}

cases <- make_cases()
res <- run_all(cases) # untimed call
times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(run_all(cases))
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(times) * 1000))
emit(res, cases)
