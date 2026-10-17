# Proof for plot.ca (ca 0.72), R side.
#
# The real plot.ca from the installed ca package runs unchanged. Its graphics
# calls (plot, points, text, lines, box, abline, axis) resolve through a shim
# environment that records the arguments and then draws, so the recorded values
# are what R draws: principal coordinates, point and label coordinates, symbols,
# colours, axis limits and axis titles. The timed runs skip the drawing and keep
# the rest of the function, which is the data computation.
#
# Output: packages/ca/docs/output/plot-ca-r-values.txt (inputs and recorded values),
#         packages/ca/docs/output/plot-ca-r-ms.txt (median of 20 timed calls).
suppressPackageStartupMessages(library(ca))
pdf(NULL)  # 7 x 7 inch device, no file written
OUT <- "packages/ca/docs/output"
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

tab <- matrix(c(12, 5, 3, 4, 11, 6, 2, 7, 13, 8, 4, 9), 4, 3, byrow = TRUE,
              dimnames = list(c("r1", "r2", "r3", "r4"), c("c1", "c2", "c3")))
O1 <- ca(tab)
# a 5 x 4 table so that the 4 x 3 active part keeps two dimensions
tab2 <- matrix(c(12, 5, 3, 8, 4, 11, 6, 4, 2, 7, 13, 9, 8, 4, 9, 6, 5, 6, 7, 10), 5, 4,
               byrow = TRUE, dimnames = list(paste0("r", 1:5), paste0("c", 1:4)))
O2 <- ca(tab2, suprow = 5, supcol = 4)

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
    add(list(kind = "text", x = xy$x, y = xy$y, labels = labels, col = d$col))
    if (st$draw) graphics::text(x, y, labels, ...)
    invisible(NULL)
  }
  e$lines <- function(x, y = NULL, ...) {
    xy <- xy.coords(x, y)
    d <- list(...)
    add(list(kind = "lines", x = xy$x, y = xy$y, col = d$col))
    if (st$draw) graphics::lines(x, y, ...)
    invisible(NULL)
  }
  e$box <- function(...) if (st$draw) graphics::box(...)
  e$abline <- function(...) if (st$draw) graphics::abline(...)
  e$axis <- function(...) if (st$draw) graphics::axis(...)
  e
}

run_plot_ca <- function(obj, ...) {
  st <- new.env()
  st$on <- TRUE
  st$draw <- TRUE
  st$calls <- list()
  st$usr <- NULL
  st$xlab <- NULL
  st$ylab <- NULL
  f <- ca:::plot.ca
  environment(f) <- make_shim(st)
  res <- f(obj, ...)
  list(st = st, res = res)
}

time_plot_ca <- function(obj, ...) {
  st <- new.env()
  st$on <- FALSE
  st$draw <- FALSE
  st$calls <- list()
  st$usr <- NULL
  f <- ca:::plot.ca
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
  emit(paste0(prefix, ".rowinertia"), obj$rowinertia)
  emit(paste0(prefix, ".colinertia"), obj$colinertia)
  emit(paste0(prefix, ".rownames"), obj$rownames)
  emit(paste0(prefix, ".colnames"), obj$colnames)
  emit(paste0(prefix, ".rowsup"), if (is.numeric(obj$rowsup)) obj$rowsup else numeric(0))
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
  A = list(obj = O1, args = list(), dim = c(1, 2)),
  B = list(obj = O2, args = list(map = "symbiplot"), dim = c(1, 2)),
  C = list(obj = O1, args = list(map = "rowgab", mass = c(TRUE, TRUE),
                                 contrib = c("relative", "absolute"),
                                 lines = c(TRUE, FALSE), labels = c(2, 1)),
           dim = c(1, 2))
)

emit_object("O1", O1)
emit_object("O2", O2)
for (label in names(cases)) {
  cs <- cases[[label]]
  rec <- do.call(run_plot_ca, c(list(cs$obj), cs$args))
  emit_case(label, rec)
}
writeLines(lines_out, file.path(OUT, "plot-ca-r-values.txt"))

ms <- time_plot_ca(O1)
writeLines(c("function\tplot.ca", "case\tA (ca(tab), default arguments)",
             paste0("median_ms\t", format(ms, digits = 17)),
             "timing\tdata computation only (drawing calls skipped), 1 untimed + 20 timed"),
           file.path(OUT, "plot-ca-r-ms.txt"))
cat("wrote", file.path(OUT, "plot-ca-r-values.txt"), "\n")
cat("median_ms", ms, "\n")
