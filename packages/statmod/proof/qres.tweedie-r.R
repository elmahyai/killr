suppressPackageStartupMessages(library(tweedie))
suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  set.seed(42)
  y <- c(0, 1.2, 0, 2.1, 0.5, 3)
  x <- c(1, 2, 1, 3, 2, 4)
  fit <- glm(y ~ x, family = tweedie(var.power = 1.5))
  set.seed(42)
  r1 <- qres.tweedie(fit)

  y2 <- c(1.2, 2.1, 0.9, 1.8, 2.4, 1.5)
  x2 <- c(1, 2, 1, 3, 2, 4)
  fit2 <- glm(y2 ~ x2, family = tweedie(var.power = 2))
  set.seed(42)
  r2 <- qres.tweedie(fit2, dispersion = 0.05)

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
