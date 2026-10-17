## recogniseCdf from goftest 1.2-3 on fixed inputs, with timings.
##
## Run from the repository root:
##   Rscript packages/goftest/proof/recogniseCdf-r.R
## Writes packages/goftest/docs/output/recogniseCdf-r.tsv, read by recogniseCdf-py.py.

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

CASES <- list("punif", "pnorm", "norm", "t", "pt", "chisq", "unif", "AD", "pAD", "CvM",
              "pCvM", "wilcox", "pwilcox", "p", "", "foo", "pfoo", "beta", "binom",
              "birthday", "tukey", "weibull", "nbinom", "logis", "lnorm", "gamma", "f",
              "geom", "hyper", "exp", "pois", "cauchy", "pexp", "pAD ", 1)

res <- list()
for (i in seq_along(CASES)) {
  r <- recogniseCdf(CASES[[i]])
  res[[paste0("s|", i)]] <- if (is.null(r)) "NULL" else r
}

ms <- time_ms(function() for (s in CASES) recogniseCdf(s))
write_out(res, ms, "recogniseCdf")
