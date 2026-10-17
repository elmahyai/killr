.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

encode_title <- function(obj, j, main) {
  title <- NULL
  if (!is.null(varnames(obj)) && is.null(main)) {
    title <- paste("Trace of", varnames(obj)[j])
  } else if (!is.null(main)) {
    title <- as.character(main)
  }
  if (is.null(title)) {
    0
  } else {
    c(-1, nchar(title), utf8ToInt(title))
  }
}

plotted <- function(obj, smooth, main) {
  chains <- mcmc.list(obj)
  out <- numeric(0)
  xp <- as.vector(time(chains))
  for (j in seq_len(nvar(chains))) {
    yp <- if (nvar(chains) > 1) chains[, j, drop = TRUE] else chains
    yp <- do.call("cbind", yp)
    out <- c(out, xp, as.numeric(yp), encode_title(chains, j, main))
    if (smooth) {
      for (k in seq_len(ncol(yp))) {
        out <- c(out, lowess(xp, yp[, k])$y)
      }
    }
  }
  out
}

build <- function() {
  n <- 2000L
  i <- seq_len(n)
  x <- cbind(
    sin(i / 3) + 0.2 * cos(i),
    cos(i / 5) + 0.01 * i,
    rep(2, n)
  )
  colnames(x) <- c("alpha", "beta", "gamma")
  y <- cbind(
    sin(i / 4) + 0.15 * cos(i / 2),
    cos(i / 6) + 0.005 * i,
    rep(1, n)
  )
  colnames(y) <- colnames(x)
  ml <- mcmc.list(mcmc(x, start = 11, thin = 2), mcmc(y, start = 11, thin = 2))
  nv <- 200L
  iv <- seq_len(nv)
  vec <- mcmc(sin(iv / 9) + 0.1 * iv, start = 5, thin = 3)
  list(ml = ml, vec = vec)
}

one <- function(save = FALSE) {
  built <- build()
  if (save) {
    svg("docs/output/traceplot-r.svg", width = 7, height = 9)
    par(mfrow = c(3, 1), mar = c(4, 4, 3, 1))
    traceplot(built$ml)
    dev.off()
  }
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  traceplot(built$ml)
  traceplot(built$vec, smooth = TRUE)
  c(plotted(built$ml, FALSE, NULL), plotted(built$vec, TRUE, NULL))
}

value <- one(TRUE)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one(FALSE)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = "proof/traceplot-r.txt")
