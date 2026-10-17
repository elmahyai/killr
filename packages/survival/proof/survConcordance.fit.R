suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

fmt <- function(x) {
  if (is.null(x)) {
    "NULL"
  } else if (length(x) == 1L && is.na(x)) {
    "NA"
  } else {
    paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.17g", v), ""), collapse = ",")
  }
}

one <- function() {
  time <- c(1, 2, 2, 2, 3, 4, 4, 4, 5, 2)
  status <- c(1, 0, 1, 0, 1, 0, 1, 1, 0, 1)
  x <- c(5, 5, 4, 4, 3, 3, 7, 6, 5, 4)
  s <- c("a", "a", "b", "b", "a", "b", "a", "b", "a", "b")
  w <- c(1, 2, 1, 1, 2, 1, 1, 0.5, 1, 1)
  start <- c(0, 0, 1, 2, 0, 3, 1, 2, 0, 4)
  stop <- c(2, 3, 4, 4, 5, 6, 6, 7, 8, 9)
  cstatus <- c(1, 0, 1, 1, 0, 1, 0, 1, 1, 0)
  xc <- c(3, 5, 2, 4, 1, 5, 3, 2, 4, 1)
  cs <- c("u", "v", "u", "v", "u", "u", "v", "v", "u", "v")
  y <- Surv(time, status)
  yc <- Surv(start, stop, cstatus)
  r1 <- suppressWarnings(survival:::survConcordance.fit(y, x))
  r2 <- suppressWarnings(survival:::survConcordance.fit(y, x, s))
  r3 <- suppressWarnings(survival:::survConcordance.fit(y, x, weight = w))
  r4 <- suppressWarnings(survival:::survConcordance.fit(yc, xc))
  r5 <- suppressWarnings(survival:::survConcordance.fit(yc, xc, cs))
  c(fmt(r1), fmt(as.vector(t(r2))), fmt(r3), fmt(r4), fmt(as.vector(t(r5))))
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
