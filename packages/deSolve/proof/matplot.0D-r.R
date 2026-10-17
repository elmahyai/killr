.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

root <- "/home/ahmed/killr_projects/killr/packages/deSolve"
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

logist <- function(t, x, parms) {
  with(as.list(parms), {
    dx <- r * x[1] * (1 - x[1] / K)
    list(dx)
  })
}

one <- function() {
  out <- vode(c(N = 0.1), seq(0, 10, 2), logist, c(r = 0.5, K = 100))
  pdf(NULL)
  matplot.0D(out)
  usr <- par("usr")
  dev.off()
  c(usr, as.vector(out[, "N"]))
}

invisible(capture.output({
  out <- vode(c(N = 0.1), seq(0, 10, 2), logist, c(r = 0.5, K = 100))
  svg(file.path(out_dir, "matplot.0D-r.svg"), width = 7, height = 5)
  matplot.0D(out)
  dev.off()
}))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value_json <- paste0("[", paste(sprintf("%.17g", value), collapse = ","), "]")
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', value_json, median(elapsed) * 1000))
