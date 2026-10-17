# Shared inputs, timing and record writing for the interp proofs.
# Run from packages/interp, for example: Rscript proof/tri.mesh-r.R

.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(interp))

# Park-Miller minimal standard generator. Integer steps below 2^53, so R and
# Python draw the same numbers.
lcg <- function(n, seed) {
  out <- numeric(n)
  s <- seed
  for (i in seq_len(n)) {
    s <- (16807 * s) %% 2147483647
    out[i] <- s / 2147483647
  }
  out
}

point_cases <- function() {
  s60 <- lcg(120, 42)
  s200 <- lcg(400, 7)
  s30 <- lcg(60, 5)
  s40 <- lcg(80, 99)
  x30 <- s30[1:30]
  y30 <- s30[31:60]
  dx <- x30[c(2, 7, 11)]
  dy <- y30[c(2, 7, 11)]
  list(
    list(id = "rand60", x = s60[1:60], y = s60[61:120], dup = "error"),
    list(id = "rand200", x = s200[1:200], y = s200[201:400], dup = "error"),
    list(id = "grid5", x = as.numeric(rep(1:5, times = 5)), y = as.numeric(rep(1:5, each = 5)), dup = "error"),
    list(id = "scaled40", x = s40[1:40] * 1000 - 500, y = s40[41:80] * 0.001, dup = "error"),
    list(id = "dups-remove", x = c(x30, dx), y = c(y30, dy), dup = "remove"),
    list(id = "dups-strip", x = c(x30, dx), y = c(y30, dy), dup = "strip"),
    list(id = "quad4", x = c(0, 2, 1, 0.2), y = c(0, 0, 1.5, 1.2), dup = "error")
  )
}

# Row-major flattening, so R and NumPy compare the same order.
rowmajor <- function(m) as.vector(t(as.matrix(m)))

# Triangles sorted within each row, rows sorted lexicographically.
# The circumcircle table follows its triangle.
canon_tri <- function(trlist, cclist) {
  v <- t(apply(trlist[, 1:3, drop = FALSE], 1, sort))
  o <- order(v[, 1], v[, 2], v[, 3])
  list(tri = v[o, , drop = FALSE], cc = cclist[o, , drop = FALSE])
}

# One untimed call is made by the caller. Returns the median of `reps` timed
# calls in milliseconds, from Sys.time().
median_ms <- function(f, reps = 20) {
  t <- numeric(reps)
  for (k in seq_len(reps)) {
    s <- Sys.time()
    f()
    t[k] <- as.numeric(difftime(Sys.time(), s, units = "secs")) * 1000
  }
  median(t)
}

# A record is a named list of numeric vectors. Each line is key TAB values.
write_record <- function(path, rec, r_ms) {
  rec[["_r_median_ms"]] <- r_ms
  lines <- vapply(names(rec), function(k) {
    vals <- sprintf("%.17g", as.numeric(rec[[k]]))
    paste0(k, "\t", paste(vals, collapse = " "))
  }, character(1))
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(lines, path)
}
