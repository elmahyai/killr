.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

encode_title <- function(title) {
  if (!nzchar(title)) return(0)
  c(-1, nchar(title), utf8ToInt(title))
}

plotted <- function(obj, lag.max = 10L) {
  obj <- mcmc.list(obj)
  out <- numeric(0)
  for (i in seq_len(nchain(obj))) {
    xacf <- acf(coda:::as.ts.mcmc(obj[[i]]), lag.max = lag.max, plot = FALSE)
    for (j in seq_len(nvar(obj))) {
      out <- c(out, -1, 1, as.numeric(xacf$lag[, j, j]), as.numeric(xacf$acf[, j, j]))
      title <- paste(
        varnames(obj)[j],
        ifelse(is.null(chanames(obj)), "", ":"),
        chanames(obj)[i],
        sep = ""
      )
      out <- c(out, encode_title(title))
    }
  }
  out
}

build <- function() {
  n <- 200L
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
  mcmc.list(mcmc(x), mcmc(y))
}

one <- function(save = FALSE) {
  obj <- build()
  if (save) {
    dir.create(file.path(root, "docs", "output"), recursive = TRUE, showWarnings = FALSE)
    svg(file.path(root, "docs", "output", "autocorr.plot-r.svg"), width = 7, height = 9)
    autocorr.plot(obj, lag.max = 10L)
    dev.off()
  }
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  autocorr.plot(obj, lag.max = 10L)
  plotted(obj, lag.max = 10L)
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
writeLines(out, con = file.path(root, "autocorr.plot-r.txt"))
