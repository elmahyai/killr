# R side of the evdistq proof. Runs the real lmom::evdistq (lmom 3.3) on a real plot.
#
# Usage: Rscript --slave evdistq-r.R <cases.json> <values.txt> <time.txt> <figure.svg>
#
# record mode: for each case, plot.new() and plot.window() set the plot region
#   (xlim, ylim, xaxs, yaxs), then the real evdistq() runs. Its lines() call is
#   masked: the line is still drawn, and its x, y, col, lty, lwd are logged.
#   par("usr") is read after the call. The case flagged "figure" is drawn on an
#   SVG device with axes; the other cases go to a null PDF device.
# time mode: the primary case. lines() is a no-op, so the timed work is the data
#   step of evdistq. One untimed call, then the median of 20 timings with Sys.time().
#
# The mask sits in the import environment of the lmom namespace, because lmom
# imports all of graphics. evdistq looks up lines() there.

args <- commandArgs(trailingOnly = TRUE)
cases_path <- args[[1]]
values_path <- args[[2]]
time_path <- args[[3]]
fig_path <- args[[4]]

lib <- Sys.getenv("LMOM_R_LIB",
  unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
suppressPackageStartupMessages(library(jsonlite))

cases <- fromJSON(cases_path, simplifyVector = TRUE,
                  simplifyDataFrame = FALSE, simplifyMatrix = FALSE)$cases
ns <- asNamespace("lmom")
imp <- parent.env(ns)

MODE <- "record"
LOG <- list()
m_lines <- function(x, y = NULL, type = "l", col = "black", lty = "solid", lwd = 1, ...) {
  if (MODE == "time") return(invisible(NULL))
  graphics::lines(x, y, type = type, col = col, lty = lty, lwd = lwd, ...)
  LOG[[length(LOG) + 1L]] <<- list(x = as.numeric(x), y = as.numeric(y),
    col = as.character(col), lty = as.character(lty), lwd = as.numeric(lwd))
  invisible(NULL)
}
unlockBinding("lines", imp)
assign("lines", m_lines, envir = imp)
lockBinding("lines", imp)

# Arguments for one evdistq call. A missing "para" key is R's missing(para).
build_args <- function(case) {
  a <- list(qfunc = get(case$qfunc, envir = ns), npoints = case$npoints)
  if (!is.null(case$para)) a$para <- case$para
  for (nm in c("col", "lty", "lwd")) if (!is.null(case[[nm]])) a[[nm]] <- case[[nm]]
  a
}

set_region <- function(case) {
  xaxs <- if (is.null(case$xaxs)) "r" else case$xaxs
  yaxs <- if (is.null(case$yaxs)) "r" else case$yaxs
  ylim <- if (is.null(case$ylim)) c(0, 1) else case$ylim
  plot.new()
  plot.window(xlim = case$xlim, ylim = ylim, xaxs = xaxs, yaxs = yaxs)
}

num_line <- function(con, field, v)
  writeLines(paste(c(field, "n", sprintf("%.17g", as.numeric(v))), collapse = "\t"), con)
str_line <- function(con, field, v)
  writeLines(paste(c(field, "s", as.character(v)), collapse = "\t"), con)

emit <- function(con, name, usr, recs) {
  writeLines(paste0("#case\t", name), con)
  for (r in recs) {
    writeLines("@record\tlines", con)
    num_line(con, "usr", usr)
    num_line(con, "x", r$x)
    num_line(con, "y", r$y)
    str_line(con, "col", r$col)
    str_line(con, "lty", r$lty)
    num_line(con, "lwd", r$lwd)
  }
}

# Record mode: one plot per case, in case order.
con <- file(values_path, "w")
for (case in cases) {
  if (isTRUE(case$figure)) {
    svg(fig_path, width = 7, height = 7)
  } else {
    pdf(NULL, width = 7, height = 7)
  }
  set_region(case)
  LOG <<- list()
  do.call(get("evdistq", envir = ns), build_args(case))
  if (isTRUE(case$figure)) {
    axis(1)
    axis(2)
  }
  usr <- as.numeric(par("usr"))
  invisible(dev.off())
  emit(con, case$name, usr, LOG)
}
close(con)

# Time mode: primary case only. One untimed call, then the median of 20.
primary <- Filter(function(c) isTRUE(c$primary), cases)[[1]]
pdf(NULL, width = 7, height = 7)
set_region(primary)
MODE <- "time"
evd <- get("evdistq", envir = ns)
a <- build_args(primary)
invisible(do.call(evd, a))
tt <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(do.call(evd, a))
  tt[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
invisible(dev.off())
writeLines(sprintf("%.17g", median(tt)), time_path)
cat("R proof done: evdistq, primary case", primary$name, "median_s", median(tt), "\n")
