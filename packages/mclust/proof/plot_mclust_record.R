# Recorder for the plot.Mclust, plot.densityMclust and densityMclust.diagnostic
# proofs. It builds on mk_recorder() in plot_record.R and adds the calls that
# recorder does not cover: an ecdf, matplot (plot.mclustBIC), rug and abline.
# legend() is layout (its position is set by the device), so it is not logged.
# Every logged record is one line in the format log_lines() writes in Python.
mk_mclust_recorder <- function(targets, rug = TRUE) {
  E <- mk_recorder(targets)
  put <- function(tag, ...) {
    E$log <- c(E$log, paste(c(tag, rec_fields(...)), collapse = " "))
    invisible(NULL)
  }
  usr <- function() as.numeric(par("usr"))

  base_plot <- E$plot
  # plot(ecdf): the knots and the heights of the step function, then the window.
  E$plot <- function(x, y = NULL, type = "p", ...) {
    if (!inherits(x, "ecdf")) return(base_plot(x, y, type = type, ...))
    if (E$mode == "time") return(invisible(NULL))
    graphics::plot(x, ...)
    put("E", environment(x)$x, environment(x)$y)
    put("W", usr())
    invisible(NULL)
  }

  # matplot(): the window, then one type "b" series per column, as Canvas.matplot logs it.
  E$matplot <- function(x, y = NULL, type = "p", pch = NULL, col = NULL, ...) {
    if (E$mode == "time") return(invisible(NULL))
    ym <- as.matrix(y)
    k <- ncol(ym)
    if (is.null(pch)) pch <- 1
    if (is.null(col)) col <- "black"
    do.call(graphics::matplot, c(list(x = x, y = y, type = type, pch = pch, col = col), list(...)))
    put("W", usr())
    pchs <- rep_len(pch, k)
    cols <- rep_len(col, k)
    for (j in seq_len(k)) put("P", x, ym[, j], type, pchs[j], cols[j])
    invisible(NULL)
  }

  # rug() is logged only where the rug is the data (densityMclust.diagnostic).
  # mclust1Dplot's uncertainty rug is left unlogged, as in the mclust1Dplot proof.
  if (rug) {
    E$rug <- function(x, ...) {
      if (E$mode != "time") put("R", x)
      invisible(NULL)
    }
  }
  E$abline <- function(a = NULL, b = NULL, h = NULL, v = NULL, ...) {
    if (E$mode != "time" && !is.null(a)) put("L", a, b)
    invisible(NULL)
  }
  E$legend <- function(...) invisible(NULL)
  # axis(1, at = G) is the tick positions of the BIC plot; logged as the axis1 value.
  E$axis <- function(side, at = NULL, ...) {
    if (E$mode != "time" && side == 1 && !is.null(at)) put("V", "axis1", as.numeric(at))
    invisible(NULL)
  }
  E
}
