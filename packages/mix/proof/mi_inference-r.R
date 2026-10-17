.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs: five imputations of four named parameters, with estimates and standard
# errors written as short decimals. mi.inference needs the parameter names. One call is
# mi.inference at confidence .95 and then at .9.
pnames <- c("a", "b", "c", "d")
est <- lapply(1:5, function(j) {
  v <- sapply(1:4, function(i) i / 2 + ((i * j * j + 3 * j) %% 7 - 3) / 10)
  names(v) <- pnames
  v
})
std <- lapply(1:5, function(j) {
  v <- sapply(1:4, function(i) 0.2 + ((i + 2 * j) %% 5) / 20)
  names(v) <- pnames
  v
})

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

keys <- c("est", "std.err", "df", "signif", "lower", "upper", "r", "fminf")

one <- function() {
  a <- mix::mi.inference(est, std, confidence = .95)
  b <- mix::mi.inference(est, std, confidence = .9)
  c(unlist(lapply(keys, function(k) num(a[[k]]))),
    unlist(lapply(keys, function(k) num(b[[k]]))))
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
