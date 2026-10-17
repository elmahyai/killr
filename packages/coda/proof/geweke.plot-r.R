.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

encode_title <- function(title) {
  c(-1, nchar(title), utf8ToInt(title))
}

plotted <- function(y, obj) {
  out <- c(as.numeric(y$z), as.numeric(y$start.iter))
  climit <- qnorm(1 - 0.05 / 2)
  for (k in seq_len(nchain(obj))) {
    for (j in seq_len(nvar(obj))) {
      z <- y$z[, j, k]
      ylimit <- max(c(climit, abs(z)))
      out <- c(out, -ylimit, ylimit, as.numeric(z))
      if (nchain(obj) > 1) {
        title <- paste(varnames(obj, allow.null = FALSE)[j], " (", chanames(obj, allow.null = FALSE)[k], ")", sep = "")
      } else {
        title <- varnames(obj, allow.null = FALSE)[j]
      }
      out <- c(out, encode_title(title))
    }
  }
  out
}

build <- function() {
  n <- 2000L
  i <- seq_len(n)
  x <- cbind(
    sin(i / 3) + 0.2 * cos(i),
    cos(i / 5) + 0.01 * i
  )
  y <- cbind(
    sin(i / 4) + 0.15 * cos(i / 2),
    cos(i / 6) + 0.005 * i
  )
  colnames(x) <- c("alpha", "beta")
  colnames(y) <- colnames(x)
  mcmc.list(mcmc(x), mcmc(y))
}

one <- function(save = FALSE) {
  obj <- build()
  if (save) {
    dir.create(file.path(root, "docs", "output"), recursive = TRUE, showWarnings = FALSE)
    svg(file.path(root, "docs", "output", "geweke.plot-r.svg"), width = 7, height = 9)
    geweke.plot(obj)
    dev.off()
  }
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  y <- geweke.plot(obj)
  plotted(y, obj)
}

value <- one(TRUE)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one(FALSE)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- vapply(value, function(v) if (is.na(v)) "null" else sprintf("%.17g", v), character(1))
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "geweke.plot-r.txt"))
