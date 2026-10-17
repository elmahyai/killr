suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

E <- mk_recorder(c("plot.qss2"))

# plot.qss2 calls plot(x, y, type = "n"), so the labels are the argument names,
# as plot.default takes them from substitute(). The wrapper records them.
E$plot <- function(x, y = NULL, type = "p", col = "black",
                   xlab = deparse(substitute(x)), ylab = deparse(substitute(y)),
                   main = "", ...) {
  xy <- xy.coords(x, y)
  E$put("T", xlab, ylab, main)
  graphics::plot(x, y, type = type, col = col, xlab = xlab, ylab = ylab, main = main, ...)
  E$put("W", as.numeric(graphics::par("usr")))
  E$put("P", xy$x, xy$y, type, canon_col(col))
  invisible(NULL)
}

# contour(interp::interp(x, y, z), add = TRUE, ...) draws the grid. The grid is
# recorded here, with NA written as 0 and a separate NA indicator.
E$contour <- function(x, ...) {
  zo <- x$z
  E$value("xo", x$x)
  E$value("yo", x$y)
  E$value("zo", ifelse(is.na(zo), 0, zo))
  E$value("zna", as.numeric(is.na(zo)))
  graphics::contour(x, ...)
  invisible(NULL)
}

d <- as.matrix(read.table(file.path(here, "..", "quantreg", "data", "check_design.txt")))
X <- cbind(d[, 2], d[, 3])
px <- X[, 1]
py <- X[, 2]
pz <- sin(2 * px) + py^2 - 0.5 * px * py
xyz <- cbind(px, py, pz)
xyz_subset <- xyz[1:25, ]

record_hull <- function(h) {
  E$value("hull_x", h$x)
  E$value("hull_y", h$y)
  E$value("hull_i", h$i)
  invisible(NULL)
}

cases <- list(
  contour_default = function() record_hull(E$plot.qss2(xyz)),
  contour_subset25 = function() record_hull(E$plot.qss2(xyz_subset)),
  contour_shifted_z = function() record_hull(E$plot.qss2(cbind(px, py, pz + 2))),
  render_unknown = function() {
    msg <- tryCatch({ E$plot.qss2(xyz, render = "bogus"); "no error" },
                    error = function(e) conditionMessage(e))
    E$log <- c(E$log, paste("ERR", msg))
  }
)

pdf(NULL)
out <- character(0)
for (nm in names(cases)) {
  E$log <- character(0)
  E$layout_logged <- FALSE
  cases[[nm]]()
  out <- c(out, paste("CASE", nm), E$log)
}
dev.off()
writeLines(out, file.path(out_dir, "plot.qss2-r.txt"))

timed <- function() plot.qss2(xyz)
pdf(NULL)
ms <- time_median_ms(timed)
dev.off()
writeLines(sprintf("%.17g", ms), file.path(out_dir, "plot.qss2-r-time.txt"))
cat("ok plot.qss2\n")
