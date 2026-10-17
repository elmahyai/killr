## pCvM from goftest 1.2-3 on fixed inputs, with timings.
##
## Run from the repository root:
##   Rscript packages/goftest/proof/pCvM-r.R
## Writes packages/goftest/docs/output/pCvM-r.tsv, read by pCvM-py.py.

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

Q <- c(0, 1 / 12, 0.02 + 0.02 * (0:29), 0.9, 1.5, 2.5, 5, 10, 20, 33, 34)
BIG_Q <- 0.001 + 0.001 * (0:1999)

res <- list()
res[["Inf|lower"]] <- pCvM(Q)
res[["5|lower"]] <- pCvM(Q, n = 5)
res[["50|lower"]] <- pCvM(Q, n = 50)
res[["1000|lower"]] <- pCvM(Q, n = 1000)
res[["Inf|upper"]] <- pCvM(Q, lower.tail = FALSE)
res[["50|upper"]] <- pCvM(Q, n = 50, lower.tail = FALSE)

ms <- time_ms(function() pCvM(BIG_Q, n = 50))
write_out(res, ms, "pCvM")
