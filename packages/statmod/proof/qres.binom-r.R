suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  yb <- c(8, 12, 5, 15, 9, 11)
  xb <- c(0, 1, 0, 1, 1, 0)
  fit_b <- glm(cbind(yb, 20 - yb) ~ xb, family = binomial)
  set.seed(42)
  r1 <- qres.binom(fit_b)

  y2 <- c(0, 1, 1, 0, 1)
  x2 <- 1:5
  fit2 <- glm(y2 ~ x2, family = binomial)
  set.seed(42)
  r2 <- qres.binom(fit2)

  fit_w <- glm(y2 ~ x2, family = binomial, weights = c(2, 3, 1, 4, 2))
  set.seed(42)
  r3 <- qres.binom(fit_w)

  c(r1, r2, r3)
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
