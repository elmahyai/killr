## cvm.test from goftest 1.2-3 on fixed inputs, with timings.
##
## Run from the repository root:
##   Rscript packages/goftest/proof/cvm-test-r.R
## Writes packages/goftest/docs/output/cvm-test-r.tsv, read by cvm-test-py.py.

lib <- Sys.getenv("GOFTEST_RLIB", "/tmp/goftest_rlib")
if (nzchar(lib) && dir.exists(lib)) .libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages(library(goftest))
stopifnot(packageDescription("goftest")$Version == "1.2-3")

GOLDEN <- 0.6180339887498949
make_sample <- function(n, family) {
  i <- seq_len(n)
  u <- if (family == "uniform") (i * GOLDEN) %% 1 else (i / (n + 1))^2
  sort(u)
}
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

res <- list()
for (fam in c("uniform", "skewed")) {
  for (n in c(5, 50, 1000)) {
    u <- make_sample(n, fam)
    z <- cvm.test(u)
    res[[sprintf("stat|%s|%g|punif", fam, n)]] <- unname(z$statistic)
    res[[sprintf("p|%s|%g|punif", fam, n)]] <- unname(z$p.value)
    z <- cvm.test(u, "pnorm", mean = 0.5, sd = 0.2)
    res[[sprintf("stat|%s|%g|pnorm", fam, n)]] <- unname(z$statistic)
    res[[sprintf("p|%s|%g|pnorm", fam, n)]] <- unname(z$p.value)
    set.seed(7)
    z <- cvm.test(u, estimated = TRUE)
    res[[sprintf("stat|%s|%g|estimated", fam, n)]] <- unname(z$statistic)
    res[[sprintf("p|%s|%g|estimated", fam, n)]] <- unname(z$p.value)
  }
}

u_big <- make_sample(10000, "uniform")
ms <- time_ms(function() cvm.test(u_big))
write_out(res, ms, "cvm-test")
