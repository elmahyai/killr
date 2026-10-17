suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  y <- c(2.1, 3.4, 2.8, 4.1, 3.0)
  x <- 1:5
  fit <- glm(y ~ x)
  r1 <- qres.default(fit)

  y2 <- c(1.5, 2.0, 2.5, 3.0)
  fit2 <- glm(y2 ~ 1, weights = c(2, 1, 3, 1))
  r2 <- qres.default(fit2, dispersion = 0.25)

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
