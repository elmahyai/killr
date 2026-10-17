.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

encode_title <- function(title) {
  if (!nzchar(title)) return(0)
  c(-1, nchar(title), utf8ToInt(title))
}

plotted <- function(m) {
  pcorr <- crosscorr(m)
  col <- topo.colors(10)
  dens <- ((pcorr + 1) * length(col)) %/% 2 + (pcorr < 1) + (pcorr < -1)
  labs <- abbreviate(varnames(m, allow.null = FALSE), minlength = 7)
  out <- c(as.numeric(pcorr))
  out <- c(out, ifelse(is.na(dens), 0, as.numeric(dens)))
  for (lab in labs) out <- c(out, encode_title(lab))
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
  as.mcmc(x)
}

one <- function(save = FALSE) {
  m <- build()
  if (save) {
    dir.create(file.path(root, "docs", "output"), recursive = TRUE, showWarnings = FALSE)
    svg(file.path(root, "docs", "output", "crosscorr.plot-r.svg"), width = 6, height = 6)
    crosscorr.plot(m)
    dev.off()
  }
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  crosscorr.plot(m)
  plotted(m)
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
writeLines(out, con = file.path(root, "crosscorr.plot-r.txt"))
