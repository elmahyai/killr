suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  y <- c(1.5, 2.2, 1.8, 3.1, 2.5)
  x <- 1:5
  fit <- glm(y ~ x, family = inverse.gaussian(link = "1/mu^2"))
  set.seed(42)
  r1 <- qres.invgauss(fit)

  y2 <- c(2.0, 3.5, 1.6, 4.2, 2.8)
  x2 <- c(1, 2, 1, 3, 2)
  fit2 <- glm(y2 ~ x2, family = inverse.gaussian(link = "1/mu^2"))
  set.seed(42)
  r2 <- qres.invgauss(fit2, dispersion = 0.05)

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
