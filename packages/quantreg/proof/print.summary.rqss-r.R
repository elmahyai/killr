suppressPackageStartupMessages(library(quantreg))
n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- sin(x) + 0.5 * z + 0.3 * sin(7 * i)
d <- data.frame(y = y, x = x, z = z)
f1 <- rqss(y ~ qss(x, lambda = 2) + z, tau = 0.5, data = d)
f2 <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1, Dorder = 0), tau = 0.5, data = d)
s1 <- summary(f1)
s2 <- summary(f2)
one <- function() {
  print.summary.rqss(s1, digits = 10)
  print.summary.rqss(s2, digits = 10)
  invisible(NULL)
}
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}

# Extract the numeric fields actually printed by print.summary.rqss. The
# printer is a plain table here; this deliberately does not claim printCoefmat
# formatting. A threshold such as "<2e-16" is represented by its bound.
number_re <- "[-+]?(?:[0-9]+\\.?[0-9]*|\\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
printed_numbers <- function(s) {
  lines <- capture.output(print.summary.rqss(s, digits = 10))
  keep <- grepl("^\\s*(\\(Intercept\\)|[xz])[[:space:]]+[-+.0-9]", lines) |
    grepl("Quantile Fidelity|Effective Degrees", lines)
  text <- paste(lines[keep], collapse = " ")
  as.numeric(unlist(regmatches(text, gregexpr(number_re, text, perl = TRUE))))
}
values <- c(as.vector(t(s1$coef)), as.vector(t(s1$qsstab)),
            s1$tau, s1$fidelity, s1$edf, s1$n,
            as.vector(t(s2$coef)), as.vector(t(s2$qsstab)),
            s2$tau, s2$fidelity, s2$edf, s2$n)
output <- file.path("packages", "quantreg", "docs", "output",
                    "print.summary.rqss-printed-values-r.txt")
writeLines(paste(sprintf("%.17g", values), collapse = ","), output)
cat(sprintf("r_ms=%.17g\n", median(elapsed) * 1000))
