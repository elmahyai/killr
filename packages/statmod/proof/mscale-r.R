suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  u1 <- c(
    -2.1, -1.4, -0.9, -0.3, 0.05, 0.2, 0.55, 0.9, 1.3, 1.8,
    -0.7, 0.1, 0.4, 0.75, 12, -9, 0.25, -0.15, 0.6, 2.2
  )
  u2 <- c(-1.1, 0.3, NA, 0.8, -0.4, 1.5, -2.0, 0.0, 0.2, NA)
  u3 <- c(0, 0, 0, 0, 0, 1.2, -0.5)
  u4 <- c(NA, NA)
  c(
    mscale(u1),
    mscale(u2),
    mscale(u2, na.rm = TRUE),
    mscale(u3),
    mscale(u4),
    mscale(u4, na.rm = TRUE)
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
