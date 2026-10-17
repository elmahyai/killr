suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

fmt <- function(x) {
  if (length(x) == 1L && is.na(x)) {
    "NA"
  } else {
    paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.17g", v), ""), collapse = ",")
  }
}

one <- function() {
  set.seed(42)
  a <- rsurvreg(8, mean = 2, scale = 5, distribution = "lognormal")
  set.seed(7)
  b <- rsurvreg(6, mean = 1, scale = 2, distribution = "weibull")
  set.seed(123)
  d <- rsurvreg(5, mean = c(0, 1, 2, 3, 4), scale = 1, distribution = "extreme")
  set.seed(2024)
  e <- rsurvreg(6, mean = 1, scale = 2, distribution = "loglogistic")
  set.seed(99)
  f <- rsurvreg(4, mean = 2, scale = 5, distribution = "gaussian")
  set.seed(5)
  g <- rsurvreg(5, mean = 0, scale = 2, distribution = "t", parms = 4)
  c(fmt(a), fmt(b), fmt(d), fmt(e), fmt(f), fmt(g))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
