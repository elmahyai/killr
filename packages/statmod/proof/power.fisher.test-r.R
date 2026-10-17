suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  c(
    power.fisher.test(0.5, 0.9, 20, 20, nsim = 100),
    power.fisher.test(0.3, 0.5, 10, 10, nsim = 50),
    power.fisher.test(0.2, 0.8, 15, 25, nsim = 80, alternative = "greater"),
    power.fisher.test(0.2, 0.8, 15, 25, nsim = 80, alternative = "less", alpha = 0.1)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
