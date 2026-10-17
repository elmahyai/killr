suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

proof_data <- function() {
  group <- c(2, 2, 2, 1, 1, 1, 2, 1)
  y <- matrix(
    c(
      1.0, 1.2, 1.1, 0.9,
      1.1, 1.3, 1.0, 1.0,
      0.9, 1.0, 1.2, 1.1,
      2.0, 2.1, 1.9, 2.2,
      2.2, 2.0, 2.3, 2.1,
      2.1, 2.4, 2.0, 2.0,
      1.0, NA, 1.1, 1.0,
      2.1, 2.0, NA, 2.2
    ),
    nrow = 8,
    ncol = 4,
    byrow = TRUE
  )
  list(group = group, y = y)
}

one <- function() {
  d <- proof_data()
  set.seed(424242)
  out <- compareTwoGrowthCurves(d$group, d$y, nsim = 80)
  c(out$stat, out$p.value)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", value), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
