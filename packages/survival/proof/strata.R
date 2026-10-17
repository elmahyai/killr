suppressPackageStartupMessages(library(survival))

serialize <- function(x) {
  c(paste(levels(x), collapse = "|"), paste(as.integer(x), collapse = "|"))
}

one <- function() {
  a <- factor(rep(1:3, 4), labels = c("low", "medium", "high"))
  b <- factor(rep(1:4, 3))
  c <- c(1L, 2L, NA, 3L, 1L)
  d <- factor(c("x", "y", "x", NA, "y"))
  s1 <- strata(b)
  s2 <- strata(a, b, shortlabel = TRUE)
  s3 <- strata(a, b, na.group = TRUE, sep = " | ")
  s4 <- strata(c, d, shortlabel = TRUE)
  c(serialize(s1), serialize(s2), serialize(s3), serialize(s4))
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
