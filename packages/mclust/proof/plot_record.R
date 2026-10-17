# Recorder shared by the mclust plot proofs (mclust graphics.R, util.R).
#
# mk_recorder(targets) returns an environment E. Each named mclust function is
# copied with E as its enclosing environment, so the drawing calls it makes
# (plot, points, lines, symbols, arrows, polygon, legend, contour, image, ...)
# reach the wrappers below. Each wrapper appends lines to E$log in the format
# that packages/mclust/mclust/plot_log.py writes (log_lines):
#     TAG f1 f2 ...      each field is its length, then its values
# Numbers are written with %.17g; strings as they are.
#
# Tags: W usr window after a plot, P points or line draw (x, y, type, pch, col),
#       U usr and panel after a points draw, A arrows, Y polygon, G legend,
#       C contour levels grid, I image grid, V named value.
#
# E$mode == "time" turns every drawing wrapper into a no-op, so a timed call
# measures the data computation of the R function and not the drawing.

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
  E <- new.env(parent = asNamespace("mclust"))
  E$mode <- "record"
  E$log <- character(0)

  put <- function(tag, ...) {
    E$log <- c(E$log, paste(c(tag, rec_fields(...)), collapse = " "))
    invisible(NULL)
  }
  usr <- function() as.numeric(par("usr"))
  mfg <- function() as.numeric(par("mfg"))[1:2]
  put_points <- function(x, y, pch, col) {
    put("P", x, y, "p", pch, col)
    put("U", usr(), mfg())
  }
  noop <- function(...) invisible(NULL)

  # plot(): draws (so the window is set), then logs the window and the
  # elements it draws. type "h" is one vertical segment per point.
  E$plot <- function(x, y = NULL, type = "p", ...) {
    if (E$mode == "time") return(invisible(NULL))
    dots <- list(...)
    graphics::plot(x, y, type = type, ...)
    put("W", usr())
    xy <- xy.coords(x, y)
    if (type == "p") {
      pch <- if (is.null(dots[["pch"]])) 1 else dots[["pch"]]
      col <- if (is.null(dots[["col"]])) "black" else dots[["col"]]
      put_points(xy$x, xy$y, pch, col)
    } else if (type %in% c("l", "b")) {
      col <- if (is.null(dots[["col"]])) "black" else dots[["col"]]
      put("P", xy$x, xy$y, type, "NA", col)
    } else if (type == "h") {
      col <- if (is.null(dots[["col"]])) "black" else dots[["col"]]
      cols <- rep(col, length.out = length(xy$x))
      for (i in seq_along(xy$x))
        put("P", c(xy$x[i], xy$x[i]), c(0, xy$y[i]), "l", "NA", cols[i])
    }
    invisible(NULL)
  }

  E$points <- function(x, y = NULL, pch = 1, col = "black", ...) {
    if (E$mode == "time") return(invisible(NULL))
    xy <- xy.coords(x, y)
    put_points(xy$x, xy$y, pch, col)
    invisible(NULL)
  }

  # vpoints() draws its symbols through symbols(); fg is the colour.
  E$symbols <- function(x, y = NULL, ..., add = FALSE, inches = TRUE,
                        fg = "black", rectangles = NULL) {
    if (E$mode == "time") return(invisible(NULL))
    xy <- xy.coords(x, y)
    put_points(xy$x, xy$y, "|", fg)
    invisible(NULL)
  }

  E$lines <- function(x, y = NULL, type = "l", pch = NULL, col = "black", ...) {
    if (E$mode == "time") return(invisible(NULL))
    xy <- xy.coords(x, y)
    put("P", xy$x, xy$y, type, "NA", col)
    invisible(NULL)
  }

  E$abline <- function(a = NULL, b = NULL, h = NULL, v = NULL, col = "black", ...) {
    if (E$mode == "time") return(invisible(NULL))
    u <- usr()
    for (hv in h) put("P", u[1:2], c(hv, hv), "l", "NA", col)
    invisible(NULL)
  }

  E$arrows <- function(x0, y0, x1 = x0, y1 = y0, ...) {
    if (E$mode == "time") return(invisible(NULL))
    put("A", x0, y0, x1, y1)
    invisible(NULL)
  }

  E$polygon <- function(x, y = NULL, col = NA, ...) {
    if (E$mode == "time") return(invisible(NULL))
    xy <- xy.coords(x, y)
    put("Y", xy$x, xy$y, col)
    invisible(NULL)
  }

  E$legend <- function(x = NULL, y = NULL, legend = NULL, pch = NULL,
                       col = NULL, ...) {
    if (E$mode == "time") return(invisible(NULL))
    put("G", x, y, legend, pch, col)
    invisible(NULL)
  }

  E$contour <- function(x, y, z, levels = NULL, ...) {
    if (E$mode == "time") return(invisible(NULL))
    put("C", x, y, as.numeric(z), levels)
    invisible(NULL)
  }

  E$.filled.contour <- function(x, y, z, levels, col) {
    if (E$mode == "time") return(invisible(NULL))
    put("C", x, y, as.numeric(z), levels)
    invisible(NULL)
  }

  # image(): logs the grid and palette, then sets the window (cell edges,
  # xaxs and yaxs "i") as image.default does.
  E$image <- function(x, y, z, col = NULL, ...) {
    if (E$mode == "time") return(invisible(NULL))
    put("I", x, y, as.numeric(z), if (is.null(col)) character(0) else col, numeric(0))
    args <- list(x = x, y = y, z = z, ...)
    if (!is.null(col)) args$col <- col
    do.call(graphics::image, args)
    put("W", usr())
    invisible(NULL)
  }

  E$pairs <- function(...) {
    if (E$mode == "time") return(invisible(NULL))
    graphics::pairs(...)
  }

  E$value <- function(name, v) {
    if (E$mode == "time") return(invisible(NULL))
    put("V", name, as.numeric(v))
    invisible(NULL)
  }

  E$title <- noop
  E$axis <- noop
  E$box <- noop
  E$rug <- noop
  E$grid <- noop
  E$mtext <- noop
  E$text <- noop

  ns <- asNamespace("mclust")
  for (nm in targets) {
    f <- get(nm, envir = ns)
    environment(f) <- E
    assign(nm, f, envir = E)
  }
  E
}

# Median of 20 timed calls after one untimed call, in milliseconds.
time_median_ms <- function(E, fn) {
  E$mode <- "time"
  fn()
  el <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    fn()
    el[[i]] <- as.numeric(Sys.time()) - t0
  }
  E$mode <- "record"
  median(el) * 1000
}

# Runs every case in record mode, writes the log, then times the case named
# `timed`. Files: <stem>-r.txt (log with CASE headers) and <stem>-r-time.txt.
proof_run <- function(E, cases, timed, stem, out_dir) {
  pdf(NULL)
  out <- character(0)
  for (nm in names(cases)) {
    E$log <- character(0)
    E$mode <- "record"
    cases[[nm]]()
    out <- c(out, paste("CASE", nm), E$log)
  }
  writeLines(out, file.path(out_dir, paste0(stem, "-r.txt")))
  ms <- time_median_ms(E, cases[[timed]])
  writeLines(sprintf("%.17g", ms), file.path(out_dir, paste0(stem, "-r-time.txt")))
  dev.off()
  invisible(ms)
}

# Shared fixtures. The same formulas are in plot_fixtures.py.
make_fixtures <- function() {
  i <- 1:60
  g3 <- (i - 1) %% 3
  x1 <- 1.3 * cos(0.37 * i) + 2.5 * g3
  x2 <- 0.9 * sin(0.53 * i) + 0.8 * g3 - 0.5
  x3 <- 0.4 * cos(0.9 * i) + 0.2 * sin(1.7 * i)
  data3 <- cbind(x = x1, y = x2, w = x3)
  data2 <- data3[, 1:2]
  cls <- ((i * 7) %% 3) + 1
  truth <- cls
  truth[c(5, 17, 33, 48)] <- (truth[c(5, 17, 33, 48)] %% 3) + 1
  mu2 <- matrix(c(0.2, -0.1, 2.4, 0.6, 1.1, 2.2), nrow = 2)
  S1 <- matrix(c(1.2, 0.4, 0.4, 0.8), 2, 2)
  S2 <- matrix(c(0.6, -0.2, -0.2, 1.1), 2, 2)
  S3 <- matrix(c(0.9, 0, 0, 0.5), 2, 2)
  sig2 <- array(0, c(2, 2, 3))
  sig2[, , 1] <- S1
  sig2[, , 2] <- S2
  sig2[, , 3] <- S3
  pro <- c(0.3, 0.4, 0.3)
  w <- sapply(1:3, function(k)
    exp(-0.5 * ((data2[, 1] - mu2[1, k])^2 + (data2[, 2] - mu2[2, k])^2)) + 1e-3)
  z <- w / rowSums(w)
  mu3 <- matrix(c(0.2, -0.1, 0.3, 2.4, 0.6, -0.4, 1.1, 2.2, 0.5), nrow = 3)
  A1 <- matrix(c(1, 0.2, 0, 0.3, 0.9, 0.1, 0, 0.2, 0.7), 3, 3)
  A2 <- matrix(c(0.8, 0, 0.3, 0.1, 1.1, 0, 0.2, 0.4, 0.6), 3, 3)
  A3 <- matrix(c(0.7, 0.1, 0.1, 0, 0.9, 0.3, 0.2, 0, 1.0), 3, 3)
  sig3 <- array(0, c(3, 3, 3))
  sig3[, , 1] <- A1 %*% t(A1) + diag(0.3, 3)
  sig3[, , 2] <- A2 %*% t(A2) + diag(0.3, 3)
  sig3[, , 3] <- A3 %*% t(A3) + diag(0.3, 3)
  list(data3 = data3, data2 = data2, cls = cls, truth = truth,
       mu2 = mu2, sig2 = sig2, pro = pro, z = z,
       mu3 = mu3, sig3 = sig3)
}
