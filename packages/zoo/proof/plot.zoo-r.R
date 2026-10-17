.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")

fmt_one <- function(z) {
  if (is.null(z)) return("null")
  if (length(z) != 1) {
    return(paste(vapply(seq_along(z), function(i) fmt_one(z[[i]]), ""), collapse = "|"))
  }
  if (is.character(z)) return(ifelse(is.na(z), "NA", z))
  if (is.logical(z)) return(ifelse(is.na(z), "NA", ifelse(z, "TRUE", "FALSE")))
  z <- as.numeric(z)
  if (is.na(z)) "NA" else if (is.infinite(z)) { if (z > 0) "Inf" else "-Inf" } else sprintf("%.16g", z)
}

fmt_vec <- function(v) {
  if (is.null(v)) return("null")
  if (length(v) == 0) return("")
  if (is.character(v) && length(v) == 1) return(ifelse(is.na(v), "NA", v))
  paste(vapply(seq_along(v), function(i) fmt_one(v[[i]]), ""), collapse = "|")
}

pch_def <- par("pch")
range2 <- function(x, ...) if (length(x) == 2) x else range(x, ...)

series_text <- function(z, name, screens = NULL, screens_missing = TRUE,
                        plot_type = NULL, plot_type_missing = TRUE,
                        col = 1, lty = 1, lwd = 1, pch = 1, type = "l", ylim = NULL) {
  nser <- NCOL(z)
  cn <- colnames(z)
  if (is.null(cn)) cn <- paste0("V", seq_len(nser))
  if (plot_type_missing) {
    if (screens_missing) plot_type <- "multiple"
    else if (length(unique(screens)) > 0) plot_type <- "single"
    else plot_type <- "multiple"
  }
  plot_type <- match.arg(plot_type, c("multiple", "single"))
  if (screens_missing) screens <- if (plot_type == "single") 1 else seq_len(nser)
  fac <- as.factor(unlist(make.par.list(cn, screens, NROW(z), nser, 1)))[drop = TRUE]
  ngraph <- nlevels(fac)
  multiple <- nser > 1 && (plot_type == "multiple" || ngraph > 1)
  if (multiple && ngraph == 1) {
    fac <- as.factor(seq_len(nser))
    ngraph <- nser
  }
  lty <- rep(lty, length.out = nser)
  lwd <- rep(lwd, length.out = nser)
  cols <- make.par.list(cn, col, NROW(z), nser, 1)
  pchs <- make.par.list(cn, pch, NROW(z), nser, pch_def)
  types <- make.par.list(cn, type, NROW(z), nser, "l")
  idx <- as.numeric(index(z))
  within <- ave(seq_along(fac), fac, FUN = seq_along)
  lines <- c(paste0("CASE ", name), paste0("mode=", if (multiple) "multiple" else "single"),
             paste0("nser=", nser))
  core <- as.numeric(coredata(z))
  dim(core) <- dim(coredata(z))
  if (is.null(dim(core))) core <- matrix(core, ncol = 1)
  if (multiple) {
    nc <- if (ngraph > 4) 2 else 1
    nr <- ceiling(ngraph / nc)
    ylim_use <- ylim
    if (!is.null(ylim_use)) {
      if (is.list(ylim_use)) ylim_use <- lapply(ylim_use, range2, na.rm = TRUE)
      else ylim_use <- list(range2(ylim_use, na.rm = TRUE))
      ylim_use <- lapply(make.par.list(cn, ylim_use, 2, nser, NULL), function(x) {
        if (is.null(x) || length(na.omit(x)) == 0) NULL else range2(x, na.rm = TRUE)
      })
    }
    lines <- c(lines, paste0("ngraph=", ngraph), paste0("nr=", nr))
    for (j in seq_along(levels(fac))) {
      lines <- c(lines, paste0("PANEL ", j))
      yl <- if (is.null(ylim_use)) NULL else ylim_use[[j]]
      lines <- c(lines, paste0("ylim=", if (is.null(yl)) "null" else fmt_vec(yl)))
      members <- which(fac == levels(fac)[j])
      for (i in members) {
        lines <- c(lines,
          paste0("series=", i),
          paste0("within=", within[[i]]),
          paste0("type=", fmt_vec(types[[i]])),
          paste0("lty=", fmt_vec(lty[[i]])),
          paste0("lwd=", fmt_vec(lwd[[i]])),
          paste0("col=", fmt_vec(cols[[i]])),
          paste0("pch=", fmt_vec(pchs[[i]])),
          paste0("x=", fmt_vec(idx)),
          paste0("y=", fmt_vec(core[, i]))
        )
      }
    }
  } else {
    if (is.null(ylim)) yl <- range(core, na.rm = TRUE)
    else yl <- range2(c(ylim, recursive = TRUE), na.rm = TRUE)
    lines <- c(lines, paste0("ylim=", fmt_vec(yl)))
    for (i in seq_len(nser)) {
      lines <- c(lines,
        paste0("series=", i),
        paste0("type=", fmt_vec(types[[i]])),
        paste0("lty=", fmt_vec(lty[[i]])),
        paste0("lwd=", fmt_vec(lwd[[i]])),
        paste0("col=", fmt_vec(cols[[i]])),
        paste0("pch=", fmt_vec(pchs[[i]])),
        paste0("x=", fmt_vec(idx)),
        paste0("y=", fmt_vec(core[, i]))
      )
    }
  }
  paste(lines, collapse = "\n")
}

scatter_text <- function(name, x, y, xy.labels = FALSE, xy.lines = NULL,
                         type = "l", type_missing = TRUE, col = 1, pch = 1, lty = 1, lwd = 1) {
  xy <- merge(x, y, all = FALSE)
  xs <- as.numeric(coredata(xy)[, 1])
  ys <- as.numeric(coredata(xy)[, 2])
  xlim <- range(xs[is.finite(xs)])
  ylim <- range(ys[is.finite(ys)])
  do.lab <- if (is.logical(xy.labels)) xy.labels else TRUE
  if (is.null(xy.lines)) xy.lines <- do.lab
  ptype <- if (do.lab) "n" else if (type_missing) "p" else type
  labels <- if (!do.lab) NULL else if (!is.logical(xy.labels)) xy.labels else index2char(index(xy))
  linetype <- if (isTRUE(xy.lines)) { if (do.lab) "c" else "l" } else NULL
  paste(c(
    paste0("CASE ", name),
    paste0("x=", fmt_vec(xs)),
    paste0("y=", fmt_vec(ys)),
    paste0("ptype=", ptype),
    paste0("lines=", if (isTRUE(xy.lines)) "1" else "0"),
    paste0("linetype=", if (is.null(linetype)) "" else linetype),
    paste0("labels=", if (is.null(labels)) "" else paste(labels, collapse = "|")),
    paste0("xlim=", fmt_vec(xlim)),
    paste0("ylim=", fmt_vec(ylim)),
    paste0("col=", fmt_vec(col)),
    paste0("pch=", fmt_vec(pch)),
    paste0("lty=", fmt_vec(lty)),
    paste0("lwd=", fmt_vec(lwd))
  ), collapse = "\n")
}

one <- function() {
  z <- zoo(cbind(A = c(1, 3, 2, 5, 4), B = c(2, 2, 4, 3, 6), C = c(0, 1, NA, 2, 3)), 1:5)
  u <- zoo(c(1, NA, 3, 4), c(10, 20, 30, 40))
  x <- zoo(c(1, 2, NA, 4), c(1, 2, 3, 4))
  y <- zoo(c(10, 20, 30, 40), c(1, 2, 3, 5))
  parts <- c(
    suppressWarnings(series_text(z, "default-multiple")),
    suppressWarnings(series_text(z, "screens-one", screens = 1, screens_missing = FALSE, col = list(B = 2))),
    suppressWarnings(series_text(z, "type-b", type = "b", pch = list(A = 1:5, B = 3), col = list(C = 4, 2))),
    suppressWarnings(series_text(z, "screens-ylim", screens = c(2, 1, 2), screens_missing = FALSE,
                                 ylim = list(c(0, 10), c(-1, 1), NULL), lty = c(2, 3), lwd = c(1, 4))),
    suppressWarnings(series_text(z, "multiple-screens-one", screens = 1, screens_missing = FALSE,
                                 plot_type = "multiple", plot_type_missing = FALSE)),
    suppressWarnings(series_text(z, "screens-range", screens = 1, screens_missing = FALSE, ylim = c(0, 1, 5))),
    suppressWarnings(series_text(z, "reversed", screens = 1, screens_missing = FALSE, ylim = c(10, 0))),
    suppressWarnings(series_text(u, "univariate", type = "o", col = 2, lwd = 3, pch = 19)),
    suppressWarnings(series_text(u, "points", type = "p", pch = 19, col = 4)),
    scatter_text("scatter", x, y),
    scatter_text("scatter-labels", x, y, xy.labels = TRUE),
    scatter_text("scatter-text", x, y, xy.labels = c("a", "b", "c"), xy.lines = FALSE),
    scatter_text("scatter-b", x, y, type = "b", type_missing = FALSE)
  )
  paste(parts, collapse = "\n\n")
}

value <- one()
out <- "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/plot.zoo-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(value, out)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"median_ms\":%.17g}\n", median(elapsed) * 1000))
