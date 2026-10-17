.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
I <- 1:12
J <- 1:4
m <- outer(I, J, function(i, j) ((i * (j + 3)) %% 17) / 3 + j)
colnames(m) <- c("a", "b", "c", "d")
rec <- new.env()
real_call <- function() {
  rec$matplot <- list()
  rec$text <- list()
  svg("/home/ahmed/killr_projects/killr/packages/MASS/docs/output/parcoord-r.svg")
  invisible(capture.output({
    trace("matplot", tracer = quote(rec$matplot[[length(rec$matplot) + 1L]] <- list(x = x, y = y)), print = FALSE, where = asNamespace("MASS"))
    trace("text.default", tracer = quote(rec$text[[length(rec$text) + 1L]] <- list(x = x, y = y, labels = labels)), print = FALSE, where = asNamespace("graphics"))
  }))
  parcoord(m, var.label = TRUE)
  usr <- par("usr")
  dev.off()
  invisible(capture.output({
    untrace("matplot", where = asNamespace("MASS"))
    untrace("text.default", where = asNamespace("graphics"))
  }))
  list(matplot = rec$matplot[[1L]], text = rec$text, usr = usr)
}
# The data part of MASS::parcoord: the column ranges and the scaled values.
data_only <- function(x) {
  rx <- apply(x, 2L, range, na.rm = TRUE)
  x <- apply(x, 2L, function(x) (x - min(x, na.rm = TRUE)) / (max(x, na.rm = TRUE) - min(x, na.rm = TRUE)))
  list(rx = rx, x = x)
}
res <- real_call()
scaled <- t(res$matplot$y)
value <- c(as.vector(scaled), res$usr[1:2], res$usr[3:4])
labels_out <- vapply(res$text, function(t) paste(trimws(t$labels), collapse = "|"), "")
writeLines(labels_out, "/home/ahmed/killr_projects/killr/packages/MASS/docs/output/parcoord-r-labels.txt")
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  data_only(m)
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
