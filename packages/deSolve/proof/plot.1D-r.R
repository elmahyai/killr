.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

root <- "/home/ahmed/killr_projects/killr/packages/deSolve"
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

make_series <- function(shift) {
  mat <- rbind(
    c(0.0, 1.0, 1.2, 1.4, 1.1,  0.10, 0.20,  0.00, -0.10, 0.30),
    c(0.5, 1.1, 1.3, 1.5, 1.2,  0.20, 0.10,  0.10, -0.20, 0.20),
    c(1.0, 1.3, 1.1, 1.6, 1.4,  0.00, 0.30,  0.20,  0.10, 0.00),
    c(1.5, 1.4, 1.5, 1.2, 1.3,  0.40, 0.20, -0.10,  0.20, 0.10)
  )
  mat[, -1] <- mat[, -1] + shift
  colnames(mat) <- c(
    "time", "A1", "A2", "A3", "A4",
    "F1", "F2", "F3", "F4", "F5"
  )
  attr(mat, "dimens") <- 4
  attr(mat, "nspec") <- 1
  attr(mat, "ynames") <- "Aphid"
  attr(mat, "lengthvar") <- c(4L, 5L)
  names(attr(mat, "lengthvar")) <- c("", "Flux")
  class(mat) <- c("deSolve", "matrix")
  mat
}

mat <- make_series(0)
mat2 <- make_series(0.25)
obs <- data.frame(x = c(0, 2), Aphid = c(0.9, 1.7), Flux = c(0.5, -0.4))
grid <- list(c(0, 1, 2, 3), c(0, 0.5, 1, 1.5, 2))

draw <- function() {
  plot.1D(
    mat, mat2,
    which = c("Aphid", "Flux"),
    type = "l",
    ask = FALSE,
    xyswap = TRUE,
    grid = grid,
    subset = c(1, 3),
    lwd = 2,
    col = c("red", "blue"),
    obs = obs
  )
}

capture_value <- function() {
  .GlobalEnv$captured <- list()
  invisible(trace(graphics::plot.default, quote({
    captured[[length(captured) + 1]] <<- list(
      x = as.numeric(x),
      y = if (is.null(y)) numeric(0) else as.numeric(y),
      xlim = if (is.null(xlim)) numeric(0) else as.numeric(xlim),
      ylim = if (is.null(ylim)) numeric(0) else as.numeric(ylim)
    )
  }), print = FALSE))
  invisible(trace(graphics::lines, quote({
    dd <- list(...)
    captured[[length(captured) + 1]] <<- list(
      x = as.numeric(x),
      y = as.numeric(dd[[1]]),
      xlim = numeric(0),
      ylim = numeric(0)
    )
  }), print = FALSE))
  invisible(trace(graphics::points, quote({
    dd <- list(...)
    captured[[length(captured) + 1]] <<- list(
      x = as.numeric(x),
      y = as.numeric(dd[[1]]),
      xlim = numeric(0),
      ylim = numeric(0)
    )
  }), print = FALSE))
  pdf(NULL)
  suppressWarnings(draw())
  junk <- dev.off()
  untrace(graphics::plot.default)
  untrace(graphics::lines)
  untrace(graphics::points)
  vals <- numeric(0)
  last_plot <- NULL
  for (item in captured) {
    # plot(type = "l") calls lines() with the same coordinates.
    if (!is.null(last_plot) &&
        length(item$xlim) == 0 &&
        length(item$x) == length(last_plot$x) &&
        length(item$y) == length(last_plot$y) &&
        isTRUE(all.equal(item$x, last_plot$x)) &&
        isTRUE(all.equal(item$y, last_plot$y))) {
      last_plot <- NULL
      next
    }
    if (length(item$xlim) > 0 || length(item$ylim) > 0) last_plot <- item
    vals <- c(vals, item$x, item$y, item$xlim, item$ylim)
  }
  vals
}

value <- capture_value()

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  pdf(NULL)
  suppressWarnings(draw())
  junk <- dev.off()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

pdf_path <- tempfile(fileext = ".pdf")
pdf(pdf_path, width = 7, height = 5)
plot.1D(mat, ask = FALSE, type = "l", lwd = 2, xyswap = TRUE)
junk <- dev.off()
svg_path <- file.path(out_dir, "plot.1D-r.svg")
status <- system2(
  "pdftocairo",
  c("-svg", "-f", "4", "-l", "4", pdf_path, svg_path),
  stdout = FALSE,
  stderr = FALSE
)
if (status != 0) stop("pdftocairo failed")

value_json <- paste0("[", paste(sprintf("%.17g", value), collapse = ","), "]")
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', value_json, median(elapsed) * 1000))
