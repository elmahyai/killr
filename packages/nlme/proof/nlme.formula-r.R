.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

height_data <- function() {
  age <- rep(c(2, 4, 6, 8, 10), 4)
  group <- factor(rep(LETTERS[1:4], each = 5))
  shift <- rep(c(-4, 1, 3, -2), each = 5)
  noise <- c(
    0.2, -0.1, 0.4, -0.3, 0.1, 0.0, 0.3, -0.2, 0.1, -0.4,
    -0.2, 0.2, 0.0, -0.1, 0.3, 0.1, -0.3, 0.2, 0.0, -0.2
  )
  height <- (100 + shift) + (15 - (100 + shift)) * exp(-exp(-3.2) * age) + noise
  data.frame(height, age, group)
}

one <- function() {
  fm <- nlme(
    height ~ SSasymp(age, Asym, R0, lrc),
    data = height_data(),
    fixed = Asym + R0 + lrc ~ 1,
    random = Asym ~ 1,
    groups = ~group,
    start = c(Asym = 100, R0 = 15, lrc = -3.2)
  )
  c(fixef(fm), fm$sigma, as.numeric(logLik(fm)), as.vector(ranef(fm)[, 1]))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
