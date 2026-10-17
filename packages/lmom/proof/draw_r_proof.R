# R side of the drawing proofs for lmrd, lmrdpoints, lmrdlines, evplot,
# evplot.default and evpoints.
#
# Usage: Rscript draw_r_proof.R <R function name> <output key> <values file> <time file>
#
# Two modes run in one process:
#   record: the real lmom function runs. Every drawing primitive it calls is
#           masked and logged, so the logged coordinates are what R draws.
#           par("usr") is read after the call.
#   time:   the same function runs with drawing primitives as no-ops, so the
#           timed work is the data computation of the function.
#
# Masks sit in the import environment of the lmom namespace, because lmom
# imports all of graphics. plot.default is swapped in the graphics namespace
# because lmrd calls graphics::plot.default directly.

args <- commandArgs(trailingOnly = TRUE)
fname <- args[[1]]
key <- args[[2]]
values_path <- args[[3]]
time_path <- args[[4]]

lib <- Sys.getenv("LMOM_R_LIB",
  unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
suppressPackageStartupMessages(library(jsonlite))

here <- {
  a <- commandArgs(trailingOnly = FALSE)
  s <- sub("^--file=", "", grep("^--file=", a, value = TRUE))
  dirname(normalizePath(s))
}
cases_all <- fromJSON(file.path(here, "draw_cases.json"), simplifyVector = TRUE,
                      simplifyDataFrame = FALSE, simplifyMatrix = FALSE)
group <- if (fname %in% c("evplot", "evplot.default")) "evplot" else fname
cases <- cases_all[[group]]

pdf(NULL, width = 7, height = 7)

MODE <- "record"
LOG <- list()
rec <- function(fn, ...) {
  LOG[[length(LOG) + 1L]] <<- c(list(.fn = fn), list(...))
  invisible(NULL)
}

ns <- asNamespace("lmom")
imp <- parent.env(ns)
mask <- function(name, f) {
  if (exists(name, envir = imp, inherits = FALSE)) {
    unlockBinding(name, imp)
    assign(name, f, envir = imp)
    lockBinding(name, imp)
  }
}

gns <- asNamespace("graphics")
orig_plot_default <- get("plot.default", envir = gns)
stub_plot_default <- function(x, y = NULL, xlim = NULL, ylim = NULL, ...)
  graphics::plot.window(xlim, ylim)
set_plot_default <- function(f) {
  unlockBinding("plot.default", gns)
  assign("plot.default", f, envir = gns)
  lockBinding("plot.default", gns)
}

m_plot <- function(x, y = NULL, xlim = NULL, ylim = NULL, type = "p", ...) {
  if (MODE == "time") return(invisible(graphics::plot.window(xlim, ylim)))
  # Log only after the frame is drawn, so a failed plot leaves no record.
  invisible(graphics::plot.default(x, y, xlim = xlim, ylim = ylim, type = type, ...))
  rec("plot", x = as.numeric(x), y = as.numeric(y), type = type)
}
m_matlines <- function(x, y, type = "l", col = "black", lty = 1, lwd = 1, ...) {
  if (MODE == "time") return(invisible(NULL))
  Y <- as.matrix(y)
  nc <- ncol(Y)
  cols <- rep_len(as.character(col), nc)
  ltys <- rep_len(as.character(lty), nc)
  lwds <- rep_len(as.numeric(lwd), nc)
  for (j in seq_len(nc))
    rec("curve", x = as.numeric(x), y = as.numeric(Y[, j]),
        col = cols[j], lty = ltys[j], lwd = lwds[j])
  invisible(NULL)
}
m_points <- function(x, y = NULL, type = "p", pch = 1, col = "black", ...) {
  if (MODE == "time") return(invisible(NULL))
  rec("points", x = as.numeric(x), y = as.numeric(y), type = type,
      pch = as.numeric(pch), col = as.character(col))
  invisible(NULL)
}
m_lines <- function(x, y = NULL, ...) {
  if (MODE == "time") return(invisible(NULL))
  rec("lines", x = as.numeric(x), y = as.numeric(y))
  invisible(NULL)
}
m_text <- function(x, y = NULL, labels = seq_along(x), ...) {
  if (MODE == "time") return(invisible(NULL))
  rec("text", x = as.numeric(x), y = as.numeric(y), labels = as.character(labels))
  invisible(NULL)
}
m_legend <- function(x = NULL, y = NULL, legend = NULL, col = NULL, lty = NULL,
                     lwd = NULL, ...) {
  if (MODE == "time") return(invisible(NULL))
  rec("legend", x = as.numeric(x), y = as.numeric(y), labels = as.character(legend),
      col = as.character(col), lty = as.character(lty), lwd = as.numeric(lwd))
  invisible(NULL)
}
m_axis <- function(side, at = NULL, labels = TRUE, pos = NA, ...) {
  if (MODE == "time") return(invisible(NULL))
  rec("axis", side = as.numeric(side), at = as.numeric(at),
      labels = as.character(labels), pos = as.numeric(pos))
  invisible(NULL)
}
m_noop <- function(...) invisible(NULL)

mask("plot", m_plot)
mask("matlines", m_matlines)
mask("points", m_points)
mask("lines", m_lines)
mask("text", m_text)
mask("legend", m_legend)
mask("axis", m_axis)
mask("box", m_noop)
mask("abline", m_noop)

# JSON arguments become R values. A JSON object is a named numeric vector for
# the point input x, and a named list everywhere else (para, legend.lmrd).
to_r_arg <- function(name, v) {
  if (is.list(v) && !is.null(names(v)) && name == "x") return(unlist(v))
  if (is.list(v) && is.null(names(v)) && all(vapply(v, is.numeric, TRUE)) &&
      length(v) > 0) return(unlist(v))
  v
}

# Convert a JSON case object into a named argument list for the function.
case_args <- function(args) {
  out <- list()
  for (nm in names(args)) {
    out[[nm]] <- if (nm == "qfunc") get(args[[nm]], envir = ns) else to_r_arg(nm, args[[nm]])
  }
  out
}

run_case <- function(case) {
  LOG <<- list()
  f <- get(fname, envir = ns)
  a <- case_args(case$args)
  if (isTRUE(case$expect_error)) {
    tryCatch(do.call(f, a), error = function(e) rec("error", message = conditionMessage(e)))
    return(LOG)
  }
  res <- do.call(f, a)
  if (group == "lmrd") {
    rec("out",
        distributions = if (is.null(res$lines)) character(0) else res$lines$distributions,
        col_lines = if (is.null(res$lines)) character(0) else as.character(res$lines$col.lines),
        lty = if (is.null(res$lines)) character(0) else as.character(res$lines$lty),
        lwd = if (is.null(res$lines)) numeric(0) else as.numeric(res$lines$lwd),
        twopar = if (is.null(res$twopar)) character(0) else res$twopar,
        pch = if (is.null(res$points)) numeric(0) else as.numeric(res$points$pch),
        col_pts = if (is.null(res$points)) character(0) else as.character(res$points$col.pts))
  }
  if (group %in% c("lmrd", "evplot")) {
    rec("usr", v = as.numeric(par("usr")))
  }
  LOG
}

emit_records <- function(con, recs) {
  for (r in recs) {
    writeLines(paste0("@record\t", r$.fn), con)
    for (nm in setdiff(names(r), ".fn")) {
      v <- r[[nm]]
      if (is.character(v)) {
        writeLines(paste(c(nm, "s", v), collapse = "\t"), con)
      } else {
        sv <- ifelse(is.na(v), "NA", sprintf("%.17g", as.numeric(v)))
        writeLines(paste(c(nm, "n", sv), collapse = "\t"), con)
      }
    }
  }
}

# Record mode: write every case.
MODE <- "record"
con <- file(values_path, "w")
for (case in cases) {
  writeLines(paste0("#case\t", case$name), con)
  recs <- run_case(case)
  emit_records(con, recs)
}
close(con)

# Time mode: primary case only. One untimed call, then median of 20.
primary <- Filter(function(c) isTRUE(c$primary), cases)[[1]]
MODE <- "time"
set_plot_default(stub_plot_default)
f <- get(fname, envir = ns)
a <- case_args(primary$args)
invisible(do.call(f, a))
tt <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(do.call(f, a))
  tt[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
set_plot_default(orig_plot_default)
writeLines(sprintf("%.17g", median(tt)), time_path)
cat("R proof done:", fname, "case", primary$name, "median_s", median(tt), "\n")
