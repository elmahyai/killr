.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

quantiles <- c(1e-4, 0.005, 0.00543, 0.01, 0.05, 0.1, 0.461, 1, 2, 10, 100)

one <- function() {
  c(pcramer(quantiles), pcramer(quantiles, eps = 1e-8))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = "proof/pcramer-r.txt")
writeLines(paste(parts, collapse = " "), con = "docs/output/pcramer-r.txt")
