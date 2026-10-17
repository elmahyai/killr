.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
i <- 1:60
x <- ((i * 37) %% 53) / 7 + 0.25 * ((i * 11) %% 5)
rec <- new.env()
rec$plot <- list()
real_call <- function() {
  rec$plot <- list()
  svg("/home/ahmed/killr_projects/killr/packages/MASS/docs/output/frequency.polygon-r.svg")
  invisible(capture.output(trace("plot.default", tracer = quote(rec$plot[[length(rec$plot) + 1L]] <- list(x = x, y = y)), print = FALSE, where = asNamespace("graphics"))))
  frequency.polygon(x, xlab = "x", ylab = "Frequency")
  invisible(capture.output(untrace("plot.default", where = asNamespace("graphics"))))
  usr <- par("usr")
  dev.off()
  list(points = rec$plot[[1L]], usr = usr)
}
data_only <- function() {
  hst <- hist(x, nclass.freq(x), probability = TRUE, plot = FALSE)
  midpoints <- 0.5 * (hst$breaks[-length(hst$breaks)] + hst$breaks[-1L])
  list(midpoints, hst$counts)
}
res <- real_call()
value <- c(res$points$x, res$points$y, res$usr[1:2], res$usr[3:4])
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  data_only()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
