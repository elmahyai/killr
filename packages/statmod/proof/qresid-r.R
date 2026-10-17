suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  y <- c(3, 7, 2, 9, 5, 4)
  x <- c(0, 1, 0, 1, 1, 0)
  fit_p <- glm(y ~ x, family = poisson)
  set.seed(42)
  r1 <- qresid(fit_p)

  y2 <- c(2.1, 3.4, 2.8, 4.1, 3.0)
  x2 <- 1:5
  fit_g <- glm(y2 ~ x2)
  r2 <- qresid(fit_g)

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
