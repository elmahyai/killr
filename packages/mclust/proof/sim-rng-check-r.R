# RNG check for the sim group (simVEV..simVVE, simulate.Mclust, simulate.densityMclust).
# The group draws only set.seed, unif_rand, rnorm (Inversion) and sample(prob=, replace=TRUE).
# Run from packages/mclust:  Rscript proof/sim-rng-check-r.R
suppressMessages(library(mclust))
dir.create("docs/output", recursive = TRUE, showWarnings = FALSE)
fmt <- function(x) sprintf("%.17g", x)
lines <- character(0)
for (s in c(1, 42, 20260917)) {
  set.seed(s)
  lines <- c(lines, paste0("seed\t", s))
  lines <- c(lines, paste(c("unif", fmt(runif(5))), collapse = "\t"))
  set.seed(s)
  lines <- c(lines, paste(c("rnorm", fmt(rnorm(20))), collapse = "\t"))
  set.seed(s)
  lines <- c(lines, paste(c("rnormfill", fmt(as.vector(matrix(rnorm(12), 4, 3)))), collapse = "\t"))
  set.seed(s)
  lines <- c(lines, paste(c("sample", as.character(sample(1:3, 50, replace = TRUE, prob = c(0.2, 0.3, 0.5)))), collapse = "\t"))
}
writeLines(lines, "docs/output/sim-rng-check-r.txt")
cat("wrote docs/output/sim-rng-check-r.txt\n")
