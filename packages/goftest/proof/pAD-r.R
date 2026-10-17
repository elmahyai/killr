## pAD from goftest 1.2-3 on fixed inputs, with timings.
##
## Run from the repository root:
##   Rscript packages/goftest/proof/pAD-r.R
## Writes packages/goftest/docs/output/pAD-r.tsv, read by pAD-py.py.

lib <- Sys.getenv("GOFTEST_RLIB", "/tmp/goftest_rlib")
if (nzchar(lib) && dir.exists(lib)) .libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages(library(goftest))
stopifnot(packageDescription("goftest")$Version == "1.2-3")

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
write_out <- function(res, ms, name) {
  out <- file.path("packages", "goftest", "docs", "output", paste0(name, "-r.tsv"))
  dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
  con <- file(out, "w")
  writeLines("kind\tcase\tindex\tvalue", con)
  for (nm in names(res)) {
    v <- res[[nm]]
    for (i in seq_along(v)) {
      s <- if (is.character(v[i])) v[i] else sprintf("%.17g", v[i])
      writeLines(sprintf("value\t%s\t%d\t%s", nm, i, s), con)
    }
  }
  writeLines(sprintf("time_ms\tmain\t0\t%.17g", ms), con)
  close(con)
  cat("wrote", out, "\n")
}

GRID <- 0.05 + 0.1 * (0:59)
BIG_GRID <- 0.05 + 0.0005 * (0:9999)
SPECIAL <- c(-Inf, -1, 0, 1e-3, 0.5, 2, 10, 50, Inf, NaN)

res <- list()
res[["grid|Inf|fast"]] <- pAD(GRID)
res[["grid|Inf|exact"]] <- pAD(GRID, fast = FALSE)
res[["grid|Inf|upper"]] <- pAD(GRID, lower.tail = FALSE)
res[["grid|5"]] <- pAD(GRID, n = 5)
res[["grid|50"]] <- pAD(GRID, n = 50)
res[["grid|1000"]] <- pAD(GRID, n = 1000)
res[["grid|50|upper"]] <- pAD(GRID, n = 50, lower.tail = FALSE)
res[["special|Inf|fast"]] <- pAD(SPECIAL)
res[["special|50"]] <- pAD(SPECIAL, n = 50)

ms <- time_ms(function() pAD(BIG_GRID))
write_out(res, ms, "pAD")
