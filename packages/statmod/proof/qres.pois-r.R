suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  y <- c(3, 7, 2, 9, 5, 4)
  x <- c(0, 1, 0, 1, 1, 0)
  fit <- glm(y ~ x, family = poisson)
  set.seed(42)
  r1 <- qres.pois(fit)

  y2 <- c(0, 1, 2, 0, 3)
  x2 <- 1:5
  fit2 <- glm(y2 ~ x2, family = poisson)
  set.seed(42)
  r2 <- qres.pois(fit2)

  y3 <- c(10, 20, 15)
  fit3 <- glm(y3 ~ 1, family = poisson)
  set.seed(42)
  r3 <- qres.pois(fit3)

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
