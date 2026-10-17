# Proof, R side: leaps 3.2 exhaustive search on the fixed design in design.csv.
#
# Run from packages/leaps/proof (see run_proof.sh). Writes:
#   ../docs/output/r_subsets.csv  selected subsets and their RSS values
#   ../docs/output/r_timings.txt  one untimed call, then 20 timed calls
#
# The R fit is the reference. It is not called from Rust or Python.

lib_dir <- Sys.getenv("LEAPS_RLIB", unset = "")
if (nzchar(lib_dir)) .libPaths(c(lib_dir, .libPaths()))
suppressPackageStartupMessages(library(leaps))

NVMAX <- 10L
NBEST <- 5L
N_TIMED <- 20L

design <- read.csv("design.csv")
y <- design$y
X <- as.matrix(design[, -1])

run_fit <- function() {
  regsubsets(x = X, y = y, nbest = NBEST, nvmax = NVMAX, method = "exhaustive")
}

# One untimed call.
fit <- run_fit()

# Median of 20 timed calls, using Sys.time().
times <- numeric(N_TIMED)
for (k in seq_len(N_TIMED)) {
  t0 <- Sys.time()
  fit <- run_fit()
  times[k] <- as.numeric(Sys.time() - t0, units = "secs")
}

# Selected subsets: for each size i (intercept included in the count) and
# rank j, the RSS and the sorted variable positions from LOPT.
# Position 1 is the intercept. Positions 2.. are predictors x1.. in order.
nvmax_eff <- fit$nvmax
ress <- fit$ress
lopt <- fit$lopt
rows <- list()
for (i in seq_len(nvmax_eff)) {
  lo <- i * (i - 1) / 2 + 1
  hi <- lo + i - 1
  for (j in seq_len(NBEST)) {
    rss <- ress[i, j]
    if (rss >= 1e35) next
    vars <- sort(lopt[lo:hi, j])
    rows[[length(rows) + 1]] <- data.frame(
      predictors = i - 1L,
      rank = j,
      rss = sprintf("%.17g", rss),
      vars = paste(vars, collapse = ";"),
      stringsAsFactors = FALSE
    )
  }
}
subsets <- do.call(rbind, rows)

out_dir <- file.path("..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(subsets, file.path(out_dir, "r_subsets.csv"), row.names = FALSE)

median_s <- median(times)
timing_lines <- c(
  sprintf("R %s, leaps %s", R.version.string, as.character(packageVersion("leaps"))),
  sprintf(
    "regsubsets(method='exhaustive') n=%d p=%d nvmax=%d nbest=%d",
    nrow(X), ncol(X), NVMAX, NBEST
  ),
  sprintf("untimed calls: 1, timed calls: %d (Sys.time)", N_TIMED),
  sprintf("timed seconds: %s", paste(sprintf("%.6f", times), collapse = " ")),
  sprintf("median_seconds: %.9f", median_s),
  sprintf("subsets_recorded: %d", nrow(subsets))
)
writeLines(timing_lines, file.path(out_dir, "r_timings.txt"))
cat(timing_lines, sep = "\n")
