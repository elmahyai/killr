# Check of the seven-digit formatting that as.matrix applies to numeric columns of a data
# frame inside imputeData. Vectors are built with integer arithmetic and literal scales,
# so the Python side builds the same doubles. Output: one line per vector, values as
# %.17g, NA as "NA", each the result of as.numeric(format(x)) (as.matrix's own step).

vec <- function(k) {
  j <- 1:37
  base <- ((j * (7L * k + 3L) + k * k * 13L) %% 1009L) - 504L
  scales <- c(1e-9, 1e-6, 1e-3, 1, 1e3, 1e6, 1e9, 1e-12, 1e12)
  s <- scales[((j + k) %% 9L) + 1L]
  den <- if (k %% 2L == 0L) 7 else 3
  x <- base / den * s
  if (k %% 5L == 0L) x <- round(x)
  x[j %% 11L == 0L] <- NA
  x
}

for (k in 1:20) {
  x <- vec(k)
  out <- as.numeric(format(x))
  cat(paste(ifelse(is.na(out), "NA", sprintf("%.17g", out)), collapse = " "), "\n")
}
