.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
mod <- function(t, x, parms) {
  with(as.list(c(x, parms)), {
    dx <- r * x[1] * (1 - x[1] / K)
    list(c(dx), prev = timestep(TRUE), curr = timestep(FALSE))
  })
}
out <- rk4(c(N = 0.1), seq(0, 10, 2), mod, c(r = 0.5, K = 100))
cat("after_rk4_timestep_prev\n")
print(timestep(TRUE))
cat("after_rk4_timestep_curr\n")
print(timestep(FALSE))
cat("global_prev_column\n")
print(out[, "prev"])
cat("global_curr_column\n")
print(out[, "curr"])
