suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  yg <- c(1.2, 2.1, 0.9, 1.8, 2.4, 1.5)
  xg <- c(1, 2, 1, 3, 2, 4)
  fit_g <- glm(yg ~ xg, family = Gamma(link = "log"))
  set.seed(42)
  r1 <- qres.gamma(fit_g)

  y2 <- c(3.1, 4.2, 2.8, 5.0, 3.9)
  x2 <- c(1, 2, 1, 3, 2)
  fit2 <- glm(y2 ~ x2, family = Gamma(link = "log"))
  set.seed(42)
  r2 <- qres.gamma(fit2, dispersion = 0.05)

  y3 <- c(2.0, 3.5, 1.8, 4.1)
  fit3 <- glm(y3 ~ 1, family = Gamma(link = "log"), weights = c(2, 1, 3, 1))
  set.seed(42)
  r3 <- qres.gamma(fit3)

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
