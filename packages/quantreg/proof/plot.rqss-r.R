suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- sin(x) + 0.5 * z + 0.3 * sin(7 * i)
d <- data.frame(y = y, x = x, z = z)
f2 <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1, Dorder = 0), tau = 0.5, data = d)
g <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1), tau = 0.5, data = d)

E <- mk_recorder(c("plot.rqss", "plot.qss1", "plot.qts1"))

# plot.rqss and its panels also call lines, matplot and title. Those are logged
# here in the same format as E$plot, so the two sides can be compared.
E$lines <- function(x, y = NULL, type = "l", col = "black", ...) {
  xy <- xy.coords(x, y)
  graphics::lines(x, y, type = type, col = col)
  E$put("P", xy$x, xy$y, type, canon_col(col))
  invisible(NULL)
}

E$matplot <- function(x, y = NULL, type = "p", xlab = "", ylab = "", ...) {
  E$put("T", xlab, ylab, "")
  graphics::matplot(x, y, type = type, xlab = xlab, ylab = ylab)
  E$put("W", as.numeric(graphics::par("usr")))
  invisible(NULL)
}

E$title <- function(main = NULL, ...) {
  E$put("T", "", "", main)
  graphics::title(main = main)
  invisible(NULL)
}

record_band <- function(b) {
  for (k in seq_along(b)) {
    if (is.list(b[[k]])) {
      E$value(sprintf("band%d_x", k), b[[k]]$x)
      E$value(sprintf("band%d_blo", k), b[[k]]$blo)
      E$value(sprintf("band%d_bhi", k), b[[k]]$bhi)
    }
  }
  invisible(NULL)
}

cases <- list(
  default_two_terms = function() record_band(E$plot.rqss(f2)),
  pointwise_bands = function() record_band(E$plot.rqss(g, bands = "pointwise")),
  both_bands_select2_titles = function() record_band(
    E$plot.rqss(g, bands = "both", select = 2, titles = c("Effect A", "Effect B"))),
  uniform_bands_pages1 = function() record_band(
    E$plot.rqss(g, bands = "uniform", pages = 1, coverage = 0.9))
)
run_cases(E, cases, file.path(out_dir, "plot.rqss-r.txt"))

timed <- function() plot.rqss(f2)
pdf(NULL)
ms <- time_median_ms(timed)
dev.off()
writeLines(sprintf("%.17g", ms), file.path(out_dir, "plot.rqss-r-time.txt"))
cat("ok plot.rqss\n")
