# Proof for the pbivnorm Rust crate: R side.
# Run from the repository root, after the R package pbivnorm 0.6.0 is installed:
#   Rscript packages/pbivnorm/proof/grid_proof_r.R
# Then run the Python side, which reads the grid and R values written here:
#   .venv/bin/python packages/pbivnorm/proof/grid_proof_py.py
# Timing: one untimed call, then the median of 20 timed calls with Sys.time().

suppressPackageStartupMessages(library(pbivnorm))

out_dir <- file.path("packages", "pbivnorm", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Grid: x and y cover -4..4, rho covers every Fortran branch, including +-1 and +-0.999.
x_grid <- seq(-4, 4, length.out = 33)
rho_grid <- c(-1, -0.999, -0.95, -0.8, -0.5, -0.25, 0, 0.25, 0.5, 0.8, 0.95, 0.999, 1)
grid <- expand.grid(x = x_grid, y = x_grid, rho = rho_grid)

fmt <- function(v) sprintf("%.17g", v)
write.csv(data.frame(x = fmt(grid$x), y = fmt(grid$y), rho = fmt(grid$rho)),
          file.path(out_dir, "grid.csv"), row.names = FALSE, quote = FALSE)

# Untimed call (warm-up).
r_values <- pbivnorm(grid$x, grid$y, grid$rho)

times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  r_values <- pbivnorm(grid$x, grid$y, grid$rho)
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}

write.csv(data.frame(r_value = fmt(r_values)),
          file.path(out_dir, "r_values.csv"), row.names = FALSE, quote = FALSE)
write.csv(data.frame(call = seq_len(20), seconds = fmt(times)),
          file.path(out_dir, "r_timings.csv"), row.names = FALSE, quote = FALSE)

cat(sprintf("R pbivnorm %s: %d points, median %.6f s over 20 calls\n",
            as.character(packageVersion("pbivnorm")), nrow(grid), median(times)))
