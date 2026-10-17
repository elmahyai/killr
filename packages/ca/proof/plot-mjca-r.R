# Proof for plot.mjca (ca 0.72), R side.
#
# The real plot.mjca from the installed ca package runs unchanged. Its graphics
# calls (plot, points, text, box, abline, axis) resolve through a shim
# environment that records the arguments and then draws, so the recorded values
# are what R draws: principal coordinates, point and label coordinates, symbols,
# colours, axis limits and axis titles. The timed runs skip the drawing and keep
# the rest of the function, which is the data computation.
#
# Output: packages/ca/docs/output/plot-mjca-r-values.txt (inputs and recorded values),
#         packages/ca/docs/output/plot-mjca-r-ms.txt (median of 20 timed calls).
suppressPackageStartupMessages(library(ca))
pdf(NULL)  # 7 x 7 inch device, no file written
OUT <- "packages/ca/docs/output"
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

dat <- data.frame(a = factor(c("x", "y", "x", "z", "y")),
                  b = factor(c("u", "u", "v", "v", "u")))
M1 <- mjca(dat, lambda = "indicator")

make_shim <- function(st) {
  e <- new.env(parent = asNamespace("ca"))
  add <- function(rec) if (st$on) st$calls[[length(st$calls) + 1L]] <- rec
  e$plot <- function(x, y = NULL, ...) {
    d <- list(...)
    st$xlab <- d$xlab
    st$ylab <- d$ylab
    if (st$draw) {
      graphics::plot(x, y, ...)
      st$usr <- par("usr")
    }
    invisible(NULL)
  }
  e$points <- function(x, y = NULL, ...) {
    xy <- xy.coords(x, y)
    d <- list(...)
    add(list(kind = "points", x = xy$x, y = xy$y, pch = d$pch, cex = d$cex, col = d$col))
    if (st$draw) graphics::points(x, y, ...)
    invisible(NULL)
  }
  e$text <- function(x, y = NULL, labels = seq_along(x), ...) {
    xy <- xy.coords(x, y)
    d <- list(...)
    # text() with no col argument draws in par("col"), which is black
    col <- if (is.null(d$col)) "black" else d$col
    add(list(kind = "text", x = xy$x, y = xy$y, labels = labels, col = col))
    if (st$draw) graphics::text(x, y, labels, ...)
    invisible(NULL)
  }
  e$box <- function(...) if (st$draw) graphics::box(...)
  e$abline <- function(...) if (st$draw) graphics::abline(...)
  e$axis <- function(...) if (st$draw) graphics::axis(...)
  e
}

run_plot_mjca <- function(obj, ...) {
  st <- new.env()
  st$on <- TRUE
  st$draw <- TRUE
  st$calls <- list()
  st$usr <- NULL
  st$xlab <- NULL
  st$ylab <- NULL
  f <- ca:::plot.mjca
  environment(f) <- make_shim(st)
  res <- f(obj, ...)
  list(st = st, res = res)
}

time_plot_mjca <- function(obj, ...) {
  st <- new.env()
  st$on <- FALSE
  st$draw <- FALSE
  st$calls <- list()
  st$usr <- NULL
  f <- ca:::plot.mjca
  environment(f) <- make_shim(st)
  f(obj, ...)  # untimed call
  t <- numeric(20)
  for (i in 1:20) {
    a <- Sys.time()
    f(obj, ...)
    t[i] <- as.numeric(Sys.time() - a) * 1000
  }
  median(t)
}

fmt <- function(v) {
  if (is.null(v) || length(v) == 0) return(character(0))
  if (is.character(v)) return(ifelse(is.na(v), "NA", v))
  if (is.logical(v)) return(ifelse(is.na(v), "NA", as.character(as.integer(v))))
  ifelse(is.na(v), "NA", sprintf("%.17g", as.numeric(v)))
}

lines_out <- character(0)
emit <- function(key, values) {
  lines_out <<- c(lines_out, paste(c(key, fmt(values)), collapse = "\t"))
}

emit_object <- function(prefix, obj) {
  emit(paste0(prefix, ".rowcoord"), as.vector(t(unname(obj$rowcoord))))
  emit(paste0(prefix, ".colcoord"), as.vector(t(unname(obj$colcoord))))
  emit(paste0(prefix, ".sv"), obj$sv)
  emit(paste0(prefix, ".rowmass"), obj$rowmass)
  emit(paste0(prefix, ".colmass"), obj$colmass)
  emit(paste0(prefix, ".rownames"), obj$rownames)
  emit(paste0(prefix, ".factornames"), obj$colnames)
  emit(paste0(prefix, ".factors"), obj$factors[, "factor"])
  emit(paste0(prefix, ".levels"), obj$factors[, "level"])
  emit(paste0(prefix, ".levels.n"), obj$levels.n)
  emit(paste0(prefix, ".lambda"), obj$lambda)
  emit(paste0(prefix, ".colsup"), if (is.numeric(obj$colsup)) obj$colsup else numeric(0))
}

emit_case <- function(label, rec) {
  emit(paste0(label, ".xlim"), rec$st$usr[1:2])
  emit(paste0(label, ".ylim"), rec$st$usr[3:4])
  emit(paste0(label, ".xlab"), rec$st$xlab)
  emit(paste0(label, ".ylab"), rec$st$ylab)
  rows <- rec$res$rows
  cols <- rec$res$cols
  emit(paste0(label, ".result.rows"), as.vector(t(unname(rows))))
  emit(paste0(label, ".result.rownames"), rownames(rows))
  emit(paste0(label, ".result.cols"), as.vector(t(unname(cols))))
  emit(paste0(label, ".result.colnames"), colnames(cols))
  for (k in seq_along(rec$st$calls)) {
    call <- rec$st$calls[[k]]
    p <- paste0(label, ".", k)
    emit(paste0(p, ".kind"), call$kind)
    emit(paste0(p, ".x"), call$x)
    emit(paste0(p, ".y"), call$y)
    if (!is.null(call$pch)) emit(paste0(p, ".pch"), call$pch)
    if (!is.null(call$cex)) emit(paste0(p, ".cex"), call$cex)
    if (!is.null(call$labels)) emit(paste0(p, ".labels"), call$labels)
    emit(paste0(p, ".col"), call$col)
  }
}

cases <- list(
  A = list(obj = M1, args = list()),
  B = list(obj = M1, args = list(what = c("all", "all"), map = "symbiplot",
                                 mass = c(TRUE, TRUE), collabels = "level")),
  C = list(obj = M1, args = list(what = c("all", "all"), map = "colprincipal",
                                 contrib = c("absolute", "absolute"),
                                 labels = c(1, 2), collabels = "factor"))
)

emit_object("M1", M1)
for (label in names(cases)) {
  cs <- cases[[label]]
  rec <- do.call(run_plot_mjca, c(list(cs$obj), cs$args))
  emit_case(label, rec)
}
writeLines(lines_out, file.path(OUT, "plot-mjca-r-values.txt"))

ms <- time_plot_mjca(M1)
writeLines(c("function\tplot.mjca", "case\tA (mjca(dat, lambda = \"indicator\"), default arguments)",
             paste0("median_ms\t", format(ms, digits = 17)),
             "timing\tdata computation only (drawing calls skipped), 1 untimed + 20 timed"),
           file.path(OUT, "plot-mjca-r-ms.txt"))
cat("wrote", file.path(OUT, "plot-mjca-r-values.txt"), "\n")
cat("median_ms", ms, "\n")
