.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(RColorBrewer))
stopifnot(packageDescription("RColorBrewer")$Version == "1.1-3")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
root <- normalizePath(file.path(dirname(script), ".."))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

brewer_all_rgb <- function(n = NULL, type = "all", select = NULL, exact.n = TRUE,
                           colorblindFriendly = FALSE) {
  gaplist <- ""
  totallist <- c(RColorBrewer:::divlist, gaplist, RColorBrewer:::quallist, gaplist,
                 RColorBrewer:::seqlist)
  gapnum <- max(c(RColorBrewer:::divnum, RColorBrewer:::qualnum, RColorBrewer:::seqnum))
  totnum <- c(RColorBrewer:::divnum, gapnum, RColorBrewer:::qualnum, gapnum,
              RColorBrewer:::seqnum)
  names(totnum) <- names(totallist)
  colorlist <- switch(type,
    div = RColorBrewer:::divlist,
    qual = RColorBrewer:::quallist,
    seq = RColorBrewer:::seqlist,
    all = totallist
  )
  maxnum <- switch(type,
    div = RColorBrewer:::divnum,
    qual = RColorBrewer:::qualnum,
    seq = RColorBrewer:::seqnum,
    all = totnum
  )
  if (!is.null(select)) {
    colorlist <- colorlist[select]
    maxnum <- maxnum[select]
  }
  if (colorblindFriendly) {
    keep <- names(colorlist) %in% c(RColorBrewer:::colorblindlist, "gap1", "gap2")
    colorlist <- colorlist[keep]
    maxnum <- maxnum[keep]
  }
  if (is.null(n)) n <- maxnum
  if (length(n) == 1) n <- rep(n, length(colorlist))
  if (exact.n) {
    keep <- n <= maxnum
    colorlist <- colorlist[keep]
    n <- n[keep]
    maxnum <- maxnum[keep]
  }
  n[n < 3] <- 3
  n[n > maxnum] <- maxnum[n > maxnum]
  rgb <- numeric()
  for (i in seq_along(colorlist)) {
    if (colorlist[[i]] == "") next
    cols <- brewer.pal(n[[i]], colorlist[[i]])
    rgb <- c(rgb, as.numeric(col2rgb(cols)) / 255)
  }
  rgb
}

one <- function() {
  pdf(NULL)
  display.brewer.all()
  usr <- par("usr")
  dev.off()
  c(brewer_all_rgb(), usr)
}

invisible(capture.output({
  svg(file.path(out_dir, "display.brewer.all-r.svg"), width = 12, height = 10)
  par(mar = c(1, 4, 1, 1))
  display.brewer.all()
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
