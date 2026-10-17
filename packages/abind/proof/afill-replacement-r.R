.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(abind))
if (packageDescription("abind")$Version != "1.4-8") stop("expected abind 1.4-8")

one <- function() {
  out <- c()

  x <- matrix(0, ncol = 3, nrow = 4, dimnames = list(letters[1:4], LETTERS[24:26]))
  y <- matrix(1:4, ncol = 2, nrow = 2, dimnames = list(letters[2:3], LETTERS[25:26]))
  afill(x) <- y
  out <- c(out, as.numeric(x))

  x3 <- array(0, dim = c(2, 4, 3), dimnames = list(LETTERS[1:2], letters[1:4], LETTERS[24:26]))
  y3 <- matrix(1:4, ncol = 2, nrow = 2, dimnames = list(letters[2:3], LETTERS[25:26]))
  afill(x3, 1, , ) <- y3
  out <- c(out, as.numeric(x3))

  x4 <- array(0, dim = c(2, 4, 3), dimnames = list(LETTERS[1:2], letters[1:4], LETTERS[24:26]))
  afill(x4, TRUE, , ) <- y3
  out <- c(out, as.numeric(x4))

  x5 <- array(0, dim = c(2, 3, 4), dimnames = list(letters[1:2], LETTERS[1:3], letters[23:26]))
  afill(x5, TRUE, , ) <- matrix(1:6, ncol = 3, dimnames = list(c("A", "B"), c("w", "x", "y")))
  out <- c(out, as.numeric(x5))

  x6 <- array(1:24, dim = c(6, 4), dimnames = list(LETTERS[1:6], letters[23:26]))
  afill(x6) <- array(-(1:6), dim = c(3, 2), dimnames = list(LETTERS[2:4], letters[24:25]))
  out <- c(out, as.numeric(x6))

  x7 <- array(1:24, dim = c(6, 4), dimnames = list(LETTERS[1:6], letters[23:26]))
  afill(x7, excess.ok = TRUE) <- array(-(1:6), dim = c(3, 2), dimnames = list(LETTERS[5:7], letters[24:25]))
  out <- c(out, as.numeric(x7))

  xv <- c(A = 0, B = 0, C = 0, D = 0)
  afill(xv) <- c(B = 1, C = 2)
  out <- c(out, as.numeric(xv))

  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17))
