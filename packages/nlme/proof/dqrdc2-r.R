## dqrdc2 kernel of nlmegls: the l_rss that gls_loglik gets from the QR of [X | y].
## Each line of data/dqrdc2-cases.txt is "n p" then n * (p + 1) values, column-major.
## R's qr.default(LAPACK = FALSE) calls the same dqrdc2 that nlme's QR() calls, at
## tol = sqrt(.Machine$double.eps). Value: log(|R[p+1, p+1]|) per case.
## Only the loop over the cases is timed; the untimed call comes first.

lines <- readLines(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE)[1])), "data", "dqrdc2-cases.txt"), warn = FALSE)
tol <- sqrt(.Machine$double.eps)

one <- function() {
  vapply(lines, function(line) {
    parts <- strsplit(line, " ", fixed = TRUE)[[1]]
    n <- as.integer(parts[1])
    p <- as.integer(parts[2])
    M <- matrix(as.numeric(parts[-(1:2)]), nrow = n, ncol = p + 1)
    q <- qr.default(M, tol = tol, LAPACK = FALSE)
    unname(log(abs(q$qr[p + 1, p + 1])))
  }, numeric(1), USE.NAMES = FALSE)
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
