.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs. Values are short binary decimals, so as.matrix's 7-digit formatting
# inside imputeData keeps them exactly. Operators are parenthesised: %% binds tighter
# than * in R.

# Case A: numeric matrix, 40 x 3, no categorical columns.
case_a <- function() {
  n <- 40L
  m <- matrix(0, n, 3)
  for (i in 1:n) for (j in 1:3) m[i, j] <- (((i * (3 * j + 4) + j * j * 7) %% 29) - 14) / 8
  m[2, 1] <- NA; m[5, 2] <- NA; m[9, 3] <- NA; m[11, 1] <- NA; m[30, 2] <- NA
  m
}

# Case B: 50 x 4 with categorical columns 1:2 (codes 1..3 and 1..2) and two continuous.
case_b <- function() {
  n <- 50L
  i <- 1:n
  c1 <- (i %% 3) + 1; c1[4] <- NA
  c2 <- ((i^2) %% 2) + 1
  x1 <- ((((i * 11)) %% 37) - 18) / 4; x1[7] <- NA
  x2 <- ((((i^2) + 3) %% 31) - 15) / 16; x2[20] <- NA
  # A data frame, because imputeData converts the categorical columns with data[[i]];
  # on a matrix that assigns single elements, not columns.
  data.frame(c1 = c1, c2 = c2, x1 = x1, x2 = x2)
}

# Case C: one continuous column, 30 rows.
case_c <- function() {
  i <- 1:30
  x <- ((((i * 5)) %% 23) - 11) / 2
  x[3] <- NA; x[17] <- NA
  matrix(x, ncol = 1)
}

# Case D: data frame with two continuous columns and no categorical argument.
case_d <- function() {
  i <- 1:25
  a <- ((((i * 3)) %% 17) - 8) / 4
  b <- ((i^2) %% 13) / 2
  a[6] <- NA; b[12] <- NA
  data.frame(a = a, b = b)
}

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  a <- mclust::imputeData(case_a(), seed = 12345)
  b <- suppressWarnings(mclust::imputeData(case_b(), categorical = c(TRUE, TRUE, FALSE, FALSE), seed = 777))
  cc <- mclust::imputeData(case_c(), seed = 2026)
  d <- mclust::imputeData(case_d(), seed = 99)
  c(num(a), num(b), num(cc), num(d))
}

value <- one()
elapsed <- numeric(20)
for (k in 1:20) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
