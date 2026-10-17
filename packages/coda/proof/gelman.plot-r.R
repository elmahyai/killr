.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

encode_title <- function(title) {
  if (is.null(title)) return(0)
  c(-1, nchar(title), utf8ToInt(title))
}

plotted <- function(y, obj) {
  out <- c(as.numeric(y$shrink), as.numeric(y$last.iter))
  all.na <- apply(is.na(y$shrink[, , 1, drop = FALSE]), 2, all)
  for (j in seq_len(nvar(obj))) {
    if (all.na[j]) next
    out <- c(out, as.numeric(y$shrink[, j, ]))
    out <- c(out, encode_title(varnames(obj)[j]))
  }
  out
}

build <- function() {
  n <- 2000L
  i <- seq_len(n)
  x1 <- cbind(sin(i / 3) + 0.2 * cos(i), cos(i / 5) + 0.01 * i)
  x2 <- cbind(sin(i / 4) + 0.15 * cos(i / 2), cos(i / 6) + 0.005 * i)
  colnames(x1) <- c("alpha", "beta")
  colnames(x2) <- colnames(x1)
  mcmc.list(mcmc(x1), mcmc(x2))
}

one <- function(save = FALSE) {
  obj <- build()
  if (save) {
    dir.create(file.path(root, "docs", "output"), recursive = TRUE, showWarnings = FALSE)
    svg(file.path(root, "docs", "output", "gelman.plot-r.svg"), width = 7, height = 5)
    gelman.plot(obj, autoburnin = FALSE)
    dev.off()
  }
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  y <- gelman.plot(obj, autoburnin = FALSE)
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
writeLines(out, con = file.path(root, "gelman.plot-r.txt"))
