# Shared trace harness for the mclust plot proofs.
#
# trace() on the graphics namespace records the calls R makes while a plot
# function runs: the window that each plot sets (par("usr") after
# plot.window), each plot.xy call (points, lines and plot with type),
# image.default, contour.default, plot.histogram and bxp. Each record is one
# tab-separated line. plot_trace.py writes the same lines from the Python
# translation, and compare_log() checks them.

.LOG <- new.env()
.LOG$out <- character(0)

.fmtn <- function(v) {
  if (is.null(v)) return("NA")
  v <- as.numeric(v)
  if (length(v) == 0) return("")
  paste(vapply(v, function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), ""), collapse = " ")
}
.fmts <- function(v) {
  if (is.null(v)) return("NA")
  if (length(v) == 0) return("")
  paste(as.character(v), collapse = " ")
}
.add <- function(tag, ...) {
  .LOG$out <- c(.LOG$out, paste(c(tag, ...), collapse = "\t"))
  invisible(NULL)
}
.value <- function(name, v) .add("V", name, .fmtn(v))

.LOG$in_legend <- FALSE

trace_start <- function() {
  ns <- asNamespace("graphics")
  .LOG$out <- character(0)
  # legend() draws its key glyphs with points(). They are layout, not data,
  # so they are left out of the log on both sides.
  trace("legend", tracer = quote(.LOG$in_legend <- TRUE),
        exit = quote(.LOG$in_legend <- FALSE), where = ns, print = FALSE)
  trace("plot.window", exit = quote(.add("W", .fmtn(par("usr")))),
        where = ns, print = FALSE)
  trace("plot.xy",
        tracer = quote(if (!identical(type, "n") && !isTRUE(.LOG$in_legend))
          .add("P", .fmtn(xy$x), .fmtn(xy$y), type,
               if (missing(pch)) "NA" else .fmts(pch),
               .fmts(if (missing(col)) "black" else col))),
        where = ns, print = FALSE)
  trace("image.default",
        tracer = quote(.add("I", .fmtn(x), .fmtn(y), .fmtn(z),
                            .fmts(if (missing(col)) "NA" else col),
                            if (missing(breaks)) "" else .fmtn(breaks))),
        where = ns, print = FALSE)
  trace("contour.default",
        tracer = quote(.add("C", .fmtn(x), .fmtn(y), .fmtn(z), .fmtn(levels))),
        where = ns, print = FALSE)
  trace("plot.histogram",
        tracer = quote(.add("H", .fmtn(x$breaks), .fmtn(x$density))),
        where = ns, print = FALSE)
  trace("bxp",
        tracer = quote(.add("B", .fmtn(z$stats))),
        where = ns, print = FALSE)
  trace("segments",
        tracer = quote(.add("S", .fmtn(c(x0, y0, x1, y1)))),
        where = ns, print = FALSE)
  invisible(NULL)
}

trace_stop <- function() {
  ns <- asNamespace("graphics")
  for (fn in c("legend", "plot.window", "plot.xy", "image.default", "contour.default",
               "plot.histogram", "bxp", "segments")) {
    untrace(fn, where = ns)
  }
  invisible(NULL)
}

trace_write <- function(path) {
  writeLines(.LOG$out, path)
  invisible(length(.LOG$out))
}
