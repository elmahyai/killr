suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  y <- c(20, 40, 40, 30)
  a <- gl(2, 1, 4)
  b <- gl(2, 2, 4)
  fit_p <- glm(y ~ a + b, family = poisson)
  z_p <- glm.scoretest(fit_p, c(0, 0, 0, 1))
  z_p2 <- glm.scoretest(fit_p, cbind(c(0, 0, 0, 1), c(1, 0, 0, 0)))

  yb <- c(8, 12, 5, 15, 9, 11)
  xb <- c(0, 1, 0, 1, 1, 0)
  fit_b <- glm(cbind(yb, 20 - yb) ~ xb, family = binomial)
  z_b <- glm.scoretest(fit_b, c(0.2, -0.1, 0.3, -0.2, 0.15, -0.05))

  yg <- c(1.2, 2.1, 0.9, 1.8, 2.4, 1.5)
  xg <- c(1, 2, 1, 3, 2, 4)
  fit_g <- glm(yg ~ xg)
  z_g <- glm.scoretest(fit_g, c(0, 1, 0, 1, 0, 1), dispersion = 0.25)

  yga <- c(3.1, 4.2, 2.8, 5.0, 3.9)
  xga <- c(1, 2, 1, 3, 2)
  fit_ga <- glm(yga ~ xga, family = Gamma(link = "log"))
  z_ga <- glm.scoretest(fit_ga, c(0.5, -0.5, 0.25, -0.25, 0.1))

  yw <- c(10, 20, 30, 40, 50)
  xw <- c(1, 2, 3, 4, 5)
  fit_w <- glm(yw ~ xw, family = poisson, weights = c(1, 0, 1, 1, 1))
  z_w <- glm.scoretest(fit_w, c(0.3, 0.7, -0.2, 0.4, 0.1))

  c(z_p, z_p2, z_b, z_g, z_ga, z_w)
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
