.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(RColorBrewer))
stopifnot(packageDescription("RColorBrewer")$Version == "1.1-3")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
root <- normalizePath(file.path(dirname(script), ".."))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

one <- function() {
  pdf(NULL)
  display.brewer.pal(7, "Greens")
  usr <- par("usr")
  dev.off()
  cols <- brewer.pal(7, "Greens")
  c(as.numeric(col2rgb(cols)) / 255, usr)
}

invisible(capture.output({
  svg(file.path(out_dir, "display.brewer.pal-r.svg"), width = 7, height = 2)
  par(mar = c(2, 0, 0, 0))
  display.brewer.pal(7, "Greens")
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
