.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
n <- 90
s <- 123
u <- numeric(2 * n)
for (k in seq_len(2 * n)) {
  s <- (16807 * s) %% 2147483647
  u[k] <- s / 2147483647
}
g <- rep(c("A", "B", "C"), each = 30)
gi <- match(g, c("A", "B", "C"))
X <- cbind(u[1:n] * 10 + 2 * gi, u[(n + 1):(2 * n)] * 6 - gi)
z <- lda(X, g)
proj <- scale(X, center = colMeans(z$means), scale = FALSE) %*% z$scaling
data <- as.vector(proj[, 1])
rec <- new.env()
real_call <- function() {
  rec$rect <- list()
  rec$lines <- list()
  rec$plot <- list()
  svg("/home/ahmed/killr_projects/killr/packages/MASS/docs/output/ldahist-r.svg")
  invisible(capture.output({
    trace("rect", tracer = quote(rec$rect[[length(rec$rect) + 1L]] <- list(xl = xleft, xr = xright, yt = ytop)), print = FALSE, where = asNamespace("MASS"))
    trace("lines.default", tracer = quote(rec$lines[[length(rec$lines) + 1L]] <- list(x = x$x, y = x$y)), print = FALSE, where = asNamespace("graphics"))
    trace("plot.default", tracer = quote(rec$plot[[length(rec$plot) + 1L]] <- list(x = x, y = y)), print = FALSE, where = asNamespace("graphics"))
  }))
  ldahist(data, g, type = "both")
  usr <- par("usr")
  dev.off()
  invisible(capture.output({
    untrace("rect", where = asNamespace("MASS"))
    untrace("lines.default", where = asNamespace("graphics"))
    untrace("plot.default", where = asNamespace("graphics"))
  }))
  list(rect = rec$rect, lines = rec$lines, plot = rec$plot, usr = usr)
}
# The data part of MASS::ldahist, with the drawing removed for timing.
data_only <- function(data, g, nbins = 25, width) {
  data <- data[!is.na(data)]
  counts <- table(g)
  groups <- names(counts)[counts > 0L]
  h <- diff(pretty(data, nbins))[1L]
  x0 <- -h / 1000
  first <- floor((min(data) - x0) / h)
  last <- ceiling((max(data) - x0) / h)
  breaks <- x0 + h * c(first:last)
  xlim <- range(breaks)
  ymax <- 0
  est <- vector("list", length(groups))
  names(est) <- groups
  for (grp in groups) {
    bin <- cut(data[g == grp], breaks, include.lowest = TRUE)
    est1 <- tabulate(bin, length(levels(bin)))
    est1 <- est1 / (diff(breaks) * length(data[g == grp]))
    ymax <- max(ymax, est1)
    est[[grp]] <- est1
  }
  xd <- vector("list", length(groups))
  for (grp in groups) {
    if (missing(width)) width <- width.SJ(data[g == grp])
    xd1 <- density(data[g == grp], n = 200L, width = width, from = xlim[1L], to = xlim[2L])
    ymax <- max(ymax, xd1$y)
    xd[[grp]] <- xd1
  }
  list(breaks = breaks, est = est, xd = xd, xlim = xlim, ymax = ymax)
}
res <- real_call()
groups <- c("A", "B", "C")
breaks <- c(res$rect[[1L]]$xl, res$rect[[1L]]$xr[length(res$rect[[1L]]$xr)])
est <- unlist(lapply(res$rect, function(r) r$yt))
dens <- unlist(lapply(res$lines, function(l) c(l$x, l$y)))
value <- c(
  res$plot[[1L]]$x, res$plot[[1L]]$y[2L],
  breaks, est, dens,
  res$usr[1:2], res$usr[3:4]
)
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  data_only(data, g)
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
