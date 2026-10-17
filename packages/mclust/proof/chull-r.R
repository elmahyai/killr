# Battery for the chull port (mclust/chull.py): R's chull(x, y) on random tie-heavy
# point sets, plus the three ellipse vertex sets that mvn2plot and mclust2Dplot draw.
# Writes one line per case: n x... y... | 1-based indices in R's final order.
.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

ellipse_xy <- function(g) {
  fx <- make_fixtures()
  mu <- fx$mu2[, g]; sigma <- fx$sig2[, , g]
  ev <- eigen(sigma, symmetric = TRUE)
  s <- sqrt(rev(sort(ev$values)))
  V <- t(ev$vectors[, rev(order(ev$values))])
  theta <- (0:15) * (pi / (2 * 15))
  x <- s[1] * cos(theta); y <- s[2] * sin(theta)
  xy <- cbind(c(x, -x, -x, x), c(y, y, -y, -y)) %*% V
  sweep(xy, MARGIN = 2, STATS = mu, FUN = "+")
}

line_of <- function(x, y, h) {
  paste(c(length(x), sprintf("%.17g", x), sprintf("%.17g", y), "|", h), collapse = " ")
}

lines <- character(0)
for (g in 1:3) {
  xy <- ellipse_xy(g)
  lines <- c(lines, paste0("ELLIPSE", g, " ", line_of(xy[, 1], xy[, 2], chull(xy))))
}

set.seed(2026)
for (t in 1:4000) {
  n <- sample(1:16, 1)
  g <- sample(1:6, 1)
  x <- sample(0:g, n, replace = TRUE) + ifelse(runif(1) < 0.3, 0.5, 0)
  y <- sample(0:g, n, replace = TRUE)
  lines <- c(lines, line_of(x, y, chull(x, y)))
}
writeLines(lines, file.path(out_dir, "chull-battery-r.txt"))
cat("wrote", length(lines), "cases\n")
