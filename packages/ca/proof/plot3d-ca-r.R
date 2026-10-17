# Proof for plot3d.ca (ca 0.72), R side.
#
# plot3d.ca draws through rgl. rgl needs an OpenGL display, which this machine
# does not have, so the proof installs a recording stand-in package named rgl into
# a temporary library. The stand-in exports the rgl functions that plot3d.ca
# calls (plot3d, lines3d, texts3d, spheres3d, triangles3d, quads3d, rgl.lines)
# and records their arguments instead of drawing. The real plot3d.ca from the
# installed ca package runs unchanged and sends its primitives to that record.
# The record is the data the 3D map is made of: axis lines, axis titles, every
# symbol vertex for each pch, and the label positions.
#
# Output: packages/ca/docs/output/plot3d-ca-r-values.txt (inputs and records),
#         packages/ca/docs/output/plot3d-ca-r-ms.txt (median of 20 timed calls).
suppressPackageStartupMessages(library(ca))
OUT <- "packages/ca/docs/output"
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

# --- recording stand-in for rgl -------------------------------------------
stub <- file.path(tempdir(), "rgl-record-stub")
stub_lib <- file.path(tempdir(), "rgl-record-lib")
dir.create(file.path(stub, "R"), recursive = TRUE, showWarnings = FALSE)
dir.create(stub_lib, showWarnings = FALSE)
writeLines(c("Package: rgl", "Version: 0.0.0.9000", "Title: Recording stand-in for rgl",
             "Description: Records the rgl calls that plot3d.ca makes; draws nothing.",
             "License: GPL-2", "Author: proof", "Maintainer: proof <proof@example.com>"),
           file.path(stub, "DESCRIPTION"))
writeLines(c("export(plot3d, lines3d, texts3d, spheres3d, triangles3d, quads3d,",
             "       rgl.lines, rgl_log, rgl_log_on)"),
           file.path(stub, "NAMESPACE"))
writeLines(c(
  ".rgl_record <- new.env()",
  ".rgl_record$on <- FALSE",
  ".rgl_record$calls <- list()",
  "rgl_log_on <- function(on) { .rgl_record$on <- on; .rgl_record$calls <- list(); invisible(NULL) }",
  "rgl_log <- function() .rgl_record$calls",
  "rec <- function(name, args) {",
  "  if (.rgl_record$on) .rgl_record$calls[[length(.rgl_record$calls) + 1L]] <- list(fn = name, args = args)",
  "  invisible(NULL)",
  "}",
  "plot3d <- function(...) rec('plot3d', list(...))",
  "lines3d <- function(...) rec('lines3d', list(...))",
  "texts3d <- function(...) rec('texts3d', list(...))",
  "spheres3d <- function(...) rec('spheres3d', list(...))",
  "triangles3d <- function(...) rec('triangles3d', list(...))",
  "quads3d <- function(...) rec('quads3d', list(...))",
  "rgl.lines <- function(...) rec('rgl.lines', list(...))"),
  file.path(stub, "R", "rgl.R"))
status <- system2("R", c("CMD", "INSTALL", "--no-help", "--no-test-load", "-l", stub_lib, stub),
                  stdout = FALSE, stderr = FALSE)
stopifnot(status == 0)
.libPaths(c(stub_lib, .libPaths()))
suppressPackageStartupMessages(library(rgl))
stopifnot(requireNamespace("rgl", quietly = TRUE))

# --- inputs -----------------------------------------------------------------
tab2 <- matrix(c(12, 5, 3, 8, 4, 11, 6, 4, 2, 7, 13, 9, 8, 4, 9, 6, 5, 6, 7, 10), 5, 4,
               byrow = TRUE, dimnames = list(paste0("r", 1:5), paste0("c", 1:4)))
tab3 <- matrix(((outer(1:6, 1:5, function(i, j) i * 7 + j * 3)) %% 13) + 1, 6, 5,
               dimnames = list(paste0("r", 1:6), paste0("c", 1:5)))
O3 <- ca(tab2)
O4 <- ca(tab3, suprow = 6, supcol = 5)

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

emit_calls <- function(label, calls) {
  for (k in seq_along(calls)) {
    call <- calls[[k]]
    p <- paste0(label, ".", k)
    a <- call$args
    named <- names(a)
    pos <- if (is.null(named)) a else a[named == ""]
    emit(paste0(p, ".fn"), call$fn)
    if (call$fn %in% c("lines3d", "spheres3d", "triangles3d", "quads3d", "texts3d")) {
      emit(paste0(p, ".x"), pos[[1]])
      emit(paste0(p, ".y"), pos[[2]])
      emit(paste0(p, ".z"), pos[[3]])
    }
    if (call$fn == "texts3d") {
      emit(paste0(p, ".text"), pos[[4]])
    } else if (call$fn == "spheres3d" && length(pos) >= 4) {
      emit(paste0(p, ".radius"), pos[[4]])
    }
    if (!is.null(a$col)) emit(paste0(p, ".col"), a$col)
    if (!is.null(a$alpha)) emit(paste0(p, ".alpha"), a$alpha)
    if (!is.null(a$cex)) emit(paste0(p, ".cex"), a$cex)
  }
}

cases <- list(
  A = list(obj = O3, args = list()),
  B = list(obj = O4, args = list(map = "symbiplot")),
  C = list(obj = O3, args = list(map = "rowprincipal", contrib = c("relative", "absolute"),
                                 labels = c(1, 2), sf = 0.001))
)

emit_object("O3", O3)
emit_object("O4", O4)
for (label in names(cases)) {
  cs <- cases[[label]]
  rgl_log_on(TRUE)
  do.call(ca:::plot3d.ca, c(list(cs$obj), cs$args))
  calls <- rgl_log()
  rgl_log_on(FALSE)
  emit_calls(label, calls)
}
writeLines(lines_out, file.path(OUT, "plot3d-ca-r-values.txt"))

# --- timing: the data computation only (the stand-in draws nothing either way) ---
time_plot3d <- function(obj, ...) {
  rgl_log_on(FALSE)
  do.call(ca:::plot3d.ca, c(list(obj), list(...)))  # untimed call
  t <- numeric(20)
  for (i in 1:20) {
    a <- Sys.time()
    do.call(ca:::plot3d.ca, c(list(obj), list(...)))
    t[i] <- as.numeric(Sys.time() - a) * 1000
  }
  median(t)
}
ms <- time_plot3d(O3)
writeLines(c("function\tplot3d.ca",
             "case\tA (ca(tab 5 x 4), default arguments)",
             paste0("median_ms\t", format(ms, digits = 17)),
             "timing\tdata computation (rgl calls are recorded, not drawn), 1 untimed + 20 timed"),
           file.path(OUT, "plot3d-ca-r-ms.txt"))
cat("wrote", file.path(OUT, "plot3d-ca-r-values.txt"), "\n")
cat("median_ms", ms, "\n")
