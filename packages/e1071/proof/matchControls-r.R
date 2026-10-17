.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
one <- function() {
  set.seed(4242)
  Age.case <- 40 + 5 * rnorm(50)
  Age.cont <- 45 + 10 * rnorm(150)
  Age <- c(Age.case, Age.cont)
  Sex.case <- sample(c("M", "F"), 50, prob = c(.4, .6), replace = TRUE)
  Sex.cont <- sample(c("M", "F"), 150, prob = c(.6, .4), replace = TRUE)
  Sex <- as.factor(c(Sex.case, Sex.cont))
  casecont <- as.factor(c(rep("case", 50), rep("cont", 150)))
  m <- matchControls(casecont ~ Sex + Age)
  fac <- as.integer(m$factor)
  fac[is.na(m$factor)] <- 0
  c(as.integer(m$controls), fac)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
