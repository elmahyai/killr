.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs. Case A: typical values. Case B: scientific notation.
case_a <- structure(list(
  G = 1:3,
  modelName = "EEE",
  obs = c(12.3456789, 3.2, 0.000123),
  boot = matrix(seq(0.5, by = 0.25, length.out = 20 * 3), nrow = 20),
  p.value = c(0.001, 0.2, 1)
), class = "mclustBootstrapLRT")

case_b <- structure(list(
  G = 1:2,
  modelName = "VVV",
  obs = c(1e-10, 2.5),
  boot = matrix(seq(1, by = 0.5, length.out = 5 * 2), nrow = 5),
  p.value = c(0.5, 0.04)
), class = "mclustBootstrapLRT")

one <- function() {
  lines <- capture.output({
    print.mclustBootstrapLRT(case_a)
    print.mclustBootstrapLRT(case_b)
  })
  lines
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
writeLines(value)
message(sprintf("%.17g", median(elapsed) * 1000))
