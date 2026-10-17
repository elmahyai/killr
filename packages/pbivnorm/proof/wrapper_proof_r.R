suppressPackageStartupMessages(library(pbivnorm))

out_dir <- file.path("packages", "pbivnorm", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

x <- c(-Inf, -3, -1, 0, 1, 3, Inf, -Inf, 0, Inf, 2, -2)
y <- c(Inf, 0.5, -0.5)
rho <- c(0, 0.25, -0.75, 0.99)

r_values <- pbivnorm(x, y, rho)
times <- numeric(20)
for (i in seq_len(20)) {
    t0 <- Sys.time()
    r_values <- pbivnorm(x, y, rho)
    times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}

fmt <- function(v) sprintf("%.17g", v)
write.csv(data.frame(r_value = fmt(r_values)),
          file.path(out_dir, "wrapper_r_values.csv"),
          row.names = FALSE, quote = FALSE)
write.csv(data.frame(seconds = fmt(times)),
          file.path(out_dir, "wrapper_r_timings.csv"),
          row.names = FALSE, quote = FALSE)
