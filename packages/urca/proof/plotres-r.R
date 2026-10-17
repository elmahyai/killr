.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
data(denmark)
sjd <- as.matrix(denmark[, c("LRM", "LRY", "IBO", "IDE")])

drawn <- function(x) {
  resids <- x@Z0 - x@Z1 %*% t(x@GAMMA) - x@ZK %*% t(x@PI)
  parts <- as.numeric(resids)
  for (i in seq_len(x@P)) {
    a <- acf(x@R0[, i], plot = FALSE)
    p <- pacf(x@R0[, i], plot = FALSE)
    clim <- qnorm((1 + 0.95) / 2) / sqrt(a$n.used)
    ylim_acf <- range(c(-clim, clim, a$acf), na.rm = TRUE)
    ylim_pacf <- range(c(-clim, clim, p$acf), na.rm = TRUE)
    parts <- c(parts, as.numeric(a$acf), as.numeric(p$acf), ylim_acf, ylim_pacf, clim)
  }
  parts
}

vecm <- NULL
one <- function() {
  vecm <<- ca.jo(sjd, ecdet = "const", type = "eigen", K = 2, spec = "longrun", season = 4)
  plotres(vecm)
}

out <- "/home/ahmed/killr_projects/killr/packages/urca/docs/output"
svg(file.path(out, "plotres-r-%02d.svg"), width = 7, height = 7, onefile = FALSE)
one()
value <- drawn(vecm)
invisible(dev.off())

tmp <- tempfile()
pdf(tmp)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
invisible(dev.off())
unlink(tmp)

cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
