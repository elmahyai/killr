# Proof for multilines (ca 0.72), R side.
#
# multilines() calls lines() once per group. This script runs the real ca
# function with its environment replaced by a shim whose lines() records its
# arguments instead of drawing, so the recorded x, y, type, col and lwd are
# exactly what R passes to the graphics device. Writes:
#   docs/output/multilines-r-values.txt  (recorded lines per case)
#   docs/output/multilines-r-ms.txt      (median of 20 timed calls after 1 untimed)
# Run from the repository root.

library(ca)

out_dir <- "packages/ca/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

rec <- new.env()
rec$calls <- list()
shim <- new.env(parent = asNamespace("ca"))
shim$lines <- function(x, y = NULL, ...) {
  if (is.matrix(x) || is.data.frame(x)) {
    xx <- as.matrix(x)
    xs <- xx[, 1]
    ys <- xx[, 2]
  } else {
    xs <- x
    ys <- y
  }
  a <- list(...)
  rec$calls[[length(rec$calls) + 1L]] <- list(
    x = as.numeric(xs), y = as.numeric(ys),
    type = a$type, col = a$col, lwd = a$lwd
  )
  invisible(NULL)
}
ml <- ca::multilines
environment(ml) <- shim

run_rec <- function(...) {
  rec$calls <- list()
  ml(...)
  rec$calls
}

fmt <- function(v) {
  if (is.null(v)) return("NA")
  if (is.character(v)) return(paste(v, collapse = "\t"))
  paste(sprintf("%.17g", as.numeric(v)), collapse = "\t")
}

write_calls <- function(label, calls, out) {
  for (k in seq_along(calls)) {
    p <- sprintf("%s.%d", label, k)
    cl <- calls[[k]]
    out <- c(out,
      paste0(p, ".x\t", fmt(cl$x)),
      paste0(p, ".y\t", fmt(cl$y)),
      paste0(p, ".type\t", fmt(cl$type)),
      paste0(p, ".col\t", fmt(cl$col)),
      paste0(p, ".lwd\t", fmt(cl$lwd))
    )
  }
  out
}

# Case A: three groups in order of first appearance (not alphabetical),
# default palette, sorted by x.
XY_A <- cbind(
  x = c(5, 1, 3, 2, 4, 9, 7, 8, 6, 10, 2, 1),
  y = c(50, 10, 30, 20, 40, 90, 70, 80, 60, 100, 25, 12)
)
grp_A <- c("zeta", "alpha", "mid", "zeta", "alpha", "mid",
           "zeta", "alpha", "mid", "zeta", "alpha", "mid")
# Case B: ten groups so that the eight-colour palette is recycled, with
# which, sort = 2 (by y), type "o" and recycled lwd.
n_B <- 60
XY_B <- cbind(x = round(seq(0, 10, length.out = n_B) + sin(1:n_B), 6),
              y = round(((1:n_B) * 37) %% 53 + 0.5, 6))
grp_B <- rep(1:10, length.out = n_B)
# Case C: no group (one line), type "p", sort = 0 (no sorting), default colour.
XY_C <- cbind(x = c(3, 1, 2, 5, 4), y = c(9, 7, 8, 1, 2))

# 2000-point timing dataset: 5 groups interleaved.
n_T <- 2000L
XY_T <- cbind(x = ((1:n_T) * 7919L) %% 1000L / 10,
              y = ((1:n_T) * 104729L) %% 997L / 7)
grp_T <- (1:n_T %% 5L) + 1L

out_lines <- c("function\tmultilines",
           "tolerance\t1e-8")
out_lines <- write_calls("A", run_rec(XY_A, group = grp_A), out_lines)
out_lines <- write_calls("B", run_rec(XY_B, group = grp_B, which = c(2, 5, 10),
                                  sort = 2, type = "o", col = c("red", "blue"),
                                  lwd = c(1, 2)), out_lines)
out_lines <- write_calls("C", run_rec(XY_C, type = "p", sort = 0), out_lines)
writeLines(out_lines, file.path(out_dir, "multilines-r-values.txt"))
cat("wrote", file.path(out_dir, "multilines-r-values.txt"), "\n")

time_ms <- function(expr_fun, repeats = 20L) {
  expr_fun()
  t <- numeric(repeats)
  for (i in seq_len(repeats)) {
    t0 <- Sys.time()
    expr_fun()
    t[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(t)
}

med <- time_ms(function() run_rec(XY_T, group = grp_T))
writeLines(c("function\tmultilines",
             "timing\tmultilines data call on 2000 points, 5 groups; 1 untimed + 20 timed",
             paste0("median_ms\t", sprintf("%.17g", med))),
           file.path(out_dir, "multilines-r-ms.txt"))
cat("median_ms", med, "\n")
