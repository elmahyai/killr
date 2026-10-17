suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  yb <- c(8, 12, 5, 15, 9, 11)
  xb <- c(0, 1, 0, 1, 1, 0)
  fit_b <- glm(cbind(yb, 20 - yb) ~ xb, family = binomial)
  set.seed(42)
  r1 <- qresiduals(fit_b)

  yg <- c(1.2, 2.1, 0.9, 1.8, 2.4, 1.5)
  xg <- c(1, 2, 1, 3, 2, 4)
  fit_ga <- glm(yg ~ xg, family = Gamma(link = "log"))
  set.seed(42)
  r2 <- qresiduals(fit_ga, dispersion = 0.05)

  c(r1, r2)
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
