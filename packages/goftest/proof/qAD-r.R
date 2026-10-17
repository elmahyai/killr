## qAD from goftest 1.2-3 on fixed inputs, with timings.
##
## Run from the repository root:
##   Rscript packages/goftest/proof/qAD-r.R
## Writes packages/goftest/docs/output/qAD-r.tsv, read by qAD-py.py.

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

P <- c(0, 0.001, 0.05 + 0.05 * (0:18), 0.99, 0.999, 1)

res <- list()
res[["Inf|fast|lower"]] <- qAD(P)
res[["Inf|exact|lower"]] <- qAD(P, fast = FALSE)
res[["Inf|fast|upper"]] <- qAD(P, lower.tail = FALSE)
res[["5|fast|lower"]] <- qAD(P, n = 5)
res[["50|fast|lower"]] <- qAD(P, n = 50)
res[["1000|fast|lower"]] <- qAD(P, n = 1000)

ms <- time_ms(function() qAD(0.05 + 0.05 * (0:18), n = 50))
write_out(res, ms, "qAD")
