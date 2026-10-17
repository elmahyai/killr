# Recorder shared by the quantreg plot proofs (quantreg quantreg.R, table.R).
#
# mk_recorder(targets) returns an environment E. Each named quantreg function is
# copied with E as its enclosing environment, so the drawing calls it makes
# (plot, points, abline, polygon, par) reach the wrappers below. Each wrapper
# draws with graphics and appends a line to E$log in the format that
# quantreg/plot.py format_log writes:
#     TAG f1 f2 ...      each field is its length, then its values
# Numbers are written with %.17g; strings as they are.
#
# Tags: T xlab ylab main, L mfrow (first par(mfrow=) of a call only),
#       W usr after a plot, P x y type col (points, line, abline span),
#       Y x y col (polygon), V name values (a returned value).

canon_col <- function(col) rgb(t(col2rgb(col)), maxColorValue = 255)

rec_fields <- function(...) {
  out <- character(0)
  for (v in list(...)) {
    if (is.null(v)) v <- numeric(0)
    if (is.character(v)) {
      out <- c(out, as.character(length(v)), v)
    } else {
      v <- as.numeric(v)
      out <- c(out, as.character(length(v)), sprintf("%.17g", v))
    }
  }
  out
}

mk_recorder <- function(targets) {
  E <- new.env(parent = asNamespace("quantreg"))
  E$log <- character(0)
  E$layout_logged <- FALSE

  # The line is built before E$log is read: a value argument can itself draw
  # (E$value(name, E$plot.rqs(...))), and that call appends to E$log.
  put <- function(tag, ...) {
    line <- paste(c(tag, rec_fields(...)), collapse = " ")
    E$log <- c(E$log, line)
    invisible(NULL)
  }
  E$put <- put

  E$plot <- function(x, y = NULL, type = "p", col = "black", xlab = "", ylab = "",
                     main = "", ylim = NULL, ...) {
    xy <- xy.coords(x, y)
    put("T", xlab, ylab, main)
    graphics::plot(x, y, type = type, col = col, xlab = xlab, ylab = ylab,
                   main = main, ylim = ylim, ...)
    put("W", as.numeric(graphics::par("usr")))
    put("P", xy$x, xy$y, type, canon_col(col))
    invisible(NULL)
  }

  E$points <- function(x, y = NULL, type = "p", col = "black", ...) {
    xy <- xy.coords(x, y)
    graphics::points(x, y, type = type, col = col, ...)
    put("P", xy$x, xy$y, type, canon_col(col))
    invisible(NULL)
  }

  E$abline <- function(a = NULL, b = NULL, h = NULL, v = NULL, col = "black", ...) {
    if (!is.null(h)) graphics::abline(h = h, col = col, ...)
    u <- as.numeric(graphics::par("usr"))
    for (hv in h) put("P", u[1:2], c(hv, hv), "l", canon_col(col))
    invisible(NULL)
  }

  E$polygon <- function(x, y = NULL, col = NA, border = NULL, ...) {
    xy <- xy.coords(x, y)
    graphics::polygon(x, y, col = col, border = border, ...)
    put("Y", xy$x, xy$y, canon_col(col))
    invisible(NULL)
  }

  # The first par(mfrow=) of a call is the layout; restores are not logged.
  E$par <- function(...) {
    r <- graphics::par(...)
    if (!E$layout_logged && "mfrow" %in% names(list(...))) {
      put("L", as.numeric(graphics::par("mfrow")))
      E$layout_logged <- TRUE
    }
    invisible(r)
  }

  E$value <- function(name, v) {
    put("V", name, as.numeric(v))
    invisible(NULL)
  }

  ns <- asNamespace("quantreg")
  for (nm in targets) {
    f <- get(nm, envir = ns)
    environment(f) <- E
    assign(nm, f, envir = E)
  }
  E
}

# Runs each case in record mode on one pdf(NULL) device and writes the log with
# CASE headers. A case is a function of no arguments that calls E$<fn>(...).
run_cases <- function(E, cases, out_file) {
  pdf(NULL)
  out <- character(0)
  for (nm in names(cases)) {
    E$log <- character(0)
    E$layout_logged <- FALSE
    cases[[nm]]()
    out <- c(out, paste("CASE", nm), E$log)
  }
  dev.off()
  writeLines(out, out_file)
}

# Median of 20 timed calls after one untimed call, in milliseconds. The timed
# function is the untouched quantreg function on the open device (no record).
time_median_ms <- function(fn) {
  fn()
  el <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    fn()
    el[[i]] <- as.numeric(Sys.time()) - t0
  }
  median(el) * 1000
}
