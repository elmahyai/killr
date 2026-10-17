suppressPackageStartupMessages(library(MASS))
suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  y <- c(5, 12, 3, 8, 15, 7)
  x <- c(0, 1, 0, 1, 1, 0)
  fit <- glm(y ~ x, family = negative.binomial(theta = 3))
  set.seed(42)
  r1 <- qres.nbinom(fit)

  y2 <- c(0, 2, 5, 1, 8)
  x2 <- 1:5
  fit2 <- glm(y2 ~ x2, family = negative.binomial(theta = 2))
  set.seed(42)
  r2 <- qres.nbinom(fit2)

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
