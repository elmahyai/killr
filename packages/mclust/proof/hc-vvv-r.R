# Proof: R mclust::hc (modelName = "VVV") and mclust:::hcVVV on fixed inputs.
# Run from packages/mclust:
#   Rscript proof/hc-vvv-r.R
# Writes docs/output/hc-vvv-r.txt: one record per line, "case|key<TAB>values".
# Keys per case: dim, hc (the 2 x m merge matrix, column-major), merge, height and
# order (as.hclust(what = "loglik") of the hc object), and time_ms, the median of
# 20 timed calls of the translated function (Sys.time, milliseconds) after one
# untimed call.
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# Fixed inputs. Case A is the MclustDA-default-r.R case A (2-D, n = 90, classes of 30).
# Case B, C and D are the other MclustDA-default-r.R inputs.
i_a <- seq_len(90L); g_a <- (i_a - 1L) %/% 30L
xa <- cbind(((i_a * 37L) %% 11L) / 11 + 2.5 * g_a + 0.05 * i_a / 90,
            ((i_a * 23L) %% 13L) / 13 + 1.5 * g_a + 0.4 * (((i_a * 37L) %% 11L) / 11) + 0.01 * i_a)

i_b <- seq_len(60L); g_b <- (i_b - 1L) %/% 30L
xb <- matrix(sin(0.37 * i_b) + 2.5 * g_b + 0.05 * i_b / 60, ncol = 1L)

mk3 <- function(i, g) {
  n <- length(i)
  x <- matrix(0, n, 3L)
  for (j in 1:3) x[, j] <- sin(0.37 * i + 1.3 * j) + 0.4 * cos(0.11 * i * j) +
    1.5 * g * (j / 3) + 0.05 * i / n * j
  x
}
i_c <- seq_len(120L); g_c <- (i_c - 1L) %/% 60L
xc <- mk3(i_c, g_c)
i_d <- seq_len(83L); g_d <- ifelse(i_d <= 40L, 0L, ifelse(i_d <= 80L, 1L, 2L))
xd <- mk3(i_d, g_d)

# The 5-point example of hcVVV-r.R.
example <- matrix(c(1, 2, 2, 1, 8, 9, 9, 8, 4, 4), ncol = 2, byrow = TRUE)

cases <- list(
  list(id = "A1-svd", fun = "hc", x = xa[g_a == 0, , drop = FALSE], use = "SVD", partition = NULL),
  list(id = "A2-svd", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "SVD", partition = NULL),
  list(id = "A3-svd", fun = "hc", x = xa[g_a == 2, , drop = FALSE], use = "SVD", partition = NULL),
  list(id = "A2-vars", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "VARS", partition = NULL),
  list(id = "A2-partition-svd", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "SVD",
       partition = rep(1:10, each = 3)),
  list(id = "A2-std", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "STD", partition = NULL),
  list(id = "A2-pcs", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "PCS", partition = NULL),
  list(id = "A2-pcr", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "PCR", partition = NULL),
  list(id = "A2-sph", fun = "hc", x = xa[g_a == 1, , drop = FALSE], use = "SPH", partition = NULL),
  list(id = "B1-svd", fun = "hc", x = xb[g_b == 0, , drop = FALSE], use = "SVD", partition = NULL),
  list(id = "C1-svd", fun = "hc", x = xc[g_c == 0, , drop = FALSE], use = "SVD", partition = NULL),
  list(id = "D1-svd", fun = "hc", x = xd[g_d == 0, , drop = FALSE], use = "SVD", partition = NULL),
  list(id = "hcVVV-example", fun = "hcVVV", x = example, use = NA, partition = c(1, 1, 2, 2, 3)),
  list(id = "hcVVV-A2", fun = "hcVVV", x = xa[g_a == 1, , drop = FALSE], use = NA, partition = NULL)
)

run_case <- function(cs) {
  if (cs$fun == "hcVVV") {
    mclust:::hcVVV(cs$x, partition = cs$partition)
  } else {
    hc(cs$x, modelName = "VVV", use = cs$use, partition = cs$partition)
  }
}

lines <- character(0)
emit <- function(id, key, values) {
  lines <<- c(lines, paste0(id, "|", key, "\t", paste(sprintf("%.17g", as.numeric(values)), collapse = " ")))
}

for (cs in cases) {
  h <- run_case(cs)
  if (cs$fun == "hcVVV") {
    # hcVVV has no hc class or data attribute: give it the ones hc() would set.
    class(h) <- "hc"
    attr(h, "data") <- cs$x
  }
  # cloglik.hc needs multivariate data (mvnXXX), so a 1-D case takes the merge heights.
  what <- if (ncol(cs$x) == 1L) "merge" else "loglik"
  hcl <- as.hclust(h, what = what)
  emit(cs$id, "dim", dim(h))
  lines <- c(lines, paste0(cs$id, "|what\t", what))
  emit(cs$id, "hc", as.vector(unclass(h)))
  emit(cs$id, "merge", as.vector(hcl$merge))
  emit(cs$id, "height", hcl$height)
  emit(cs$id, "order", hcl$order)
}

# Timing: one untimed call, then the median of 20 timed calls of the translated function.
for (cs in cases) {
  run_case(cs)
  elapsed <- numeric(20)
  for (k in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    run_case(cs)
    elapsed[k] <- as.numeric(Sys.time()) - t0
  }
  emit(cs$id, "time_ms", median(elapsed) * 1000)
}

writeLines(lines, "docs/output/hc-vvv-r.txt")
cat(length(lines), "records written to docs/output/hc-vvv-r.txt\n")
