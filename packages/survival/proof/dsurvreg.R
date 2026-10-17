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
  x <- c(1:10, 0.5, NA)
  a <- dsurvreg(x, 2, 5, distribution = "lognormal")
  b <- dsurvreg(c(0.5, 1, 2, 3), 2, 3, distribution = "weibull")
  c <- dsurvreg(1:5, 0, 1, distribution = "extreme")
  d <- dsurvreg(c(1, 2, 3), 1, 2, distribution = "loglogistic")
  e <- dsurvreg(2.5, 2, 5, distribution = "gaussian")
  f <- dsurvreg(c(0.2, 1, 4), 0, 2, distribution = "t", parms = 4)
  c(fmt(a), fmt(b), fmt(c), fmt(d), fmt(e), fmt(f))
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
