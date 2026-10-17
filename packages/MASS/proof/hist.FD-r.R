.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
i <- 1:60
x <- ((i * 37) %% 53) / 7 + 0.25 * ((i * 11) %% 5)
real_call <- function() {
  svg("/home/ahmed/killr_projects/killr/packages/MASS/docs/output/hist.FD-r.svg")
  h <- hist.FD(x)
  usr <- par("usr")
  dev.off()
  list(h = h, usr = usr)
}
data_only <- function() {
  nc <- nclass.FD(x)
  hist(x, nc, probability = TRUE, plot = FALSE)
}
res <- real_call()
h <- res$h
value <- c(h$breaks, h$counts, h$density, h$mids, res$usr[1:2], res$usr[3:4])
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  data_only()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
