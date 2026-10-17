.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")

y <- c(
  7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6, 7, 10, 6, 12,
  6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5, 3, 3, 4
)
lag1 <- c(
  0, 7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6, 7, 10,
  6, 12, 6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5, 3, 3
)
lag2 <- c(
  0, 0, 7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6, 7,
  10, 6, 12, 6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5, 3
)
lag3 <- c(
  0, 0, 0, 7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6,
  7, 10, 6, 12, 6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5
)

proof_vector <- function(conv) {
  fam <- conv$call$family
  class_map <- c(negbin = 1, glm = 2, lm = 3)
  c(
    coef(conv),
    conv$theta,
    conv$deviance,
    conv$df.residual,
    conv$rank,
    fam$theta,
    class_map[class(conv)[1]],
    class_map[class(conv)[2]],
    as.numeric(is.null(conv$call$init.theta)),
    as.numeric(is.null(conv$call$link)),
    as.numeric(deparse(conv$call[[1L]]) == "stats::glm"),
    as.numeric(deparse(fam[[1L]]) == "negative.binomial"),
    as.numeric(deparse(fam$link) == "log")
  )
}

one <- function() {
  fit <- glm.nb(
    y ~ lag1 + lag2 + lag3,
    data = data.frame(y = y, lag1 = lag1, lag2 = lag2, lag3 = lag3),
    link = identity,
    start = c(2, 0.1, 0.1, 0.1)
  )
  proof_vector(glm.convert(fit))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
