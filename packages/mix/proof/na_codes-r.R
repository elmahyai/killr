.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# The three internal helpers of mix: .na.to.snglcode, .na.to.icode, .code.to.na.
snglcode <- mix:::.na.to.snglcode
icode <- mix:::.na.to.icode
code2na <- mix:::.code.to.na

x <- c(1.5, NA, -2.25, 999, NA, 0.125, 7, 999, NA, -0.5)
m <- matrix(c(1, NA, 3, 2, 999, NA, 1, 2, 3, NA), 5)

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

one <- function() {
  c(num(snglcode(x, 999)), num(icode(x, 1)), num(code2na(x, 999)),
    num(snglcode(m, 0)), num(icode(m, 9)), num(code2na(m, 999)))
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
