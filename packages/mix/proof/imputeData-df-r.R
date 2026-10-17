# Proof inputs for imputeData on a numeric array and on data frames (mclust 6.1.3, mix 1.0-13).
# Values are short binary decimals or built from integer arithmetic, so the Python side
# builds the same doubles. Each case prints a header "# name nrow ncol categorical-columns",
# then its imputed values one per line in column-major order (NA as "NA"). After the cases,
# the median of 20 timed calls of the whole set, in milliseconds.

# Numeric array: 40 x 3, no categorical columns.
array_a <- function() {
  n <- 40L
  m <- matrix(0, n, 3)
  for (i in 1:n) for (j in 1:3) m[i, j] <- (((i * (3 * j + 4) + j * j * 7) %% 29) - 14) / 8
  m[2, 1] <- NA; m[5, 2] <- NA; m[9, 3] <- NA; m[11, 1] <- NA; m[30, 2] <- NA
  m
}

# Numeric array: 30 x 1.
array_c <- function() {
  i <- 1:30
  x <- ((((i * 5)) %% 23) - 11) / 2
  x[3] <- NA; x[17] <- NA
  matrix(x, ncol = 1)
}

# Data frame with two factor columns (labels "1".."3" and "1","2"), two numeric columns with
# non-terminating decimals, and one numeric column that spans several magnitudes.
frame_mixed <- function() {
  n <- 36L
  i <- 1:n
  c1 <- factor((i %% 3) + 1)
  c2 <- factor(((i * i) %% 2) + 1)
  x1 <- ((((i * 11)) %% 37) - 18) / 7; x1[7] <- NA
  x2 <- ((((i^2) + 3) %% 31) - 15) / 3; x2[20] <- NA
  x3 <- ((((i * 5)) %% 13) - 6) / 7 * c(1e-9, 1, 1e6, 1e-3)[((i %% 4) + 1)]; x3[12] <- NA
  data.frame(c1 = c1, x1 = x1, c2 = c2, x2 = x2, x3 = x3)
}

# Data frame with two numeric columns only.
frame_numeric <- function() {
  i <- 1:25
  a <- ((((i * 3)) %% 17) - 8) / 7
  b <- ((i^2) %% 13) / 3
  a[6] <- NA; b[12] <- NA
  data.frame(a = a, b = b)
}

run_all <- function() {
  lines <- character(0)
  a <- mclust::imputeData(array_a(), seed = 12345)
  c_out <- mclust::imputeData(array_c(), seed = 2026)
  dn <- suppressWarnings(mclust::imputeData(frame_mixed(), seed = 4242))
  dc <- suppressWarnings(mclust::imputeData(frame_mixed(), categorical = c(TRUE, FALSE, TRUE, FALSE, FALSE), seed = 4242))
  dnum <- mclust::imputeData(frame_numeric(), seed = 99)
  parts <- list(
    list("array_a", a, integer(0)),
    list("array_c", c_out, integer(0)),
    list("frame_null", dn, integer(0)),
    list("frame_categorical", dc, c(1L, 3L)),
    list("frame_numeric", dnum, integer(0))
  )
  for (p in parts) {
    out <- as.matrix(p[[2]])
    lines <- c(lines, sprintf("# %s %d %d %s", p[[1]], nrow(out), ncol(out), paste(p[[3]], collapse = ",")))
    for (v in as.vector(out)) lines <- c(lines, if (is.na(v)) "NA" else sprintf("%.17g", v))
  }
  lines
}

value <- run_all()
elapsed <- numeric(20)
for (k in 1:20) {
  t0 <- as.numeric(Sys.time())
  invisible(run_all())
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "\n")
cat("\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
