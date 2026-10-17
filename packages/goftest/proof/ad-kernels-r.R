## ad-kernels-r.R
##
## Reference values and timings from goftest 1.2-3 (compiled R package),
## for the Anderson-Darling kernels in src/AnDarl.c and src/ADinf.c.
##
## Run from the repository root:
##   Rscript packages/goftest/proof/ad-kernels-r.R
##
## Writes packages/goftest/docs/output/ad-kernels-r.tsv, which
## ad-kernels-py.py reads.

lib <- Sys.getenv("GOFTEST_RLIB", "/tmp/goftest_rlib")
if (nzchar(lib) && dir.exists(lib)) .libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages(library(goftest))
stopifnot(packageDescription("goftest")$Version == "1.2-3")

GOLDEN <- 0.6180339887498949
FAMILIES <- c("uniform", "skewed")
NS <- c(5, 50, 1000)
GRID <- 0.05 + 0.1 * (0:59)
BIG_GRID <- 0.05 + 0.0005 * (0:9999)
BIG_N <- 10000

make_sample <- function(n, family) {
  i <- seq_len(n)
  u <- if (family == "uniform") (i * GOLDEN) %% 1 else (i / (n + 1))^2
  sort(u)
}

## Values -----------------------------------------------------------------

results <- list()

for (fam in FAMILIES) {
  for (n in NS) {
    u <- make_sample(n, fam)
    z <- ad.test(u)
    results[[paste0("ad_test_stat|", fam, "|", n)]] <- unname(z$statistic)
    results[[paste0("ad_test_p|", fam, "|", n)]] <- unname(z$p.value)
  }
}

results[["adinf_approx|grid"]] <- unname(pAD(GRID))
results[["adinf_exact|grid"]] <- unname(pAD(GRID, fast = FALSE))
for (n in NS) {
  results[[paste0("ad_prob_n|", n, "|grid")]] <- unname(pAD(GRID, n = n))
}

## Timings: one untimed call, then median of 20 timed calls (ms) ---------

time_ms <- function(f, reps = 20) {
  f()
  t <- numeric(reps)
  for (k in seq_len(reps)) {
    t0 <- Sys.time()
    f()
    t[k] <- as.numeric(Sys.time() - t0, units = "secs") * 1000
  }
  median(t)
}

u_big <- make_sample(BIG_N, "uniform")
timings <- c(
  ad_test   = time_ms(function() goftest:::simpleADtest(u_big)),
  ad_prob_n = time_ms(function() pAD(BIG_GRID, n = 50)),
  adinf     = time_ms(function() pAD(BIG_GRID)),
  ad_inf    = time_ms(function() pAD(BIG_GRID, fast = FALSE))
)

## Write ------------------------------------------------------------------

outdir <- file.path("packages", "goftest", "docs", "output")
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
out <- file.path(outdir, "ad-kernels-r.tsv")
con <- file(out, "w")
writeLines("kind\tcase\tindex\tvalue", con)
for (nm in names(results)) {
  v <- results[[nm]]
  writeLines(sprintf("value\t%s\t%d\t%s", nm, seq_along(v), sprintf("%.17g", v)), con)
}
for (nm in names(timings)) {
  writeLines(sprintf("time_ms\t%s\t0\t%.17g", nm, timings[[nm]]), con)
}
close(con)

cat("goftest version:", as.character(packageDescription("goftest")$Version), "\n")
cat("R version:", R.version.string, "\n")
cat("value cases:", length(results), "\n")
cat(sprintf("time_ms %-10s %.6f\n", names(timings), timings), sep = "")
cat("wrote", out, "\n")
