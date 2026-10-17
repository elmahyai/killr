suppressPackageStartupMessages({library(quantreg); library(SparseM)})
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

d <- as.matrix(read.table(file.path(here, "..", "quantreg", "data", "check_design.txt")))
X <- cbind(d[, 2], d[, 3])
px <- X[, 1]
py <- X[, 2]
pz <- sin(2 * px) + py^2 - 0.5 * px * py
obj <- cbind(px, py, pz)
dimnames(obj) <- list(NULL, c("x", "y", "zfit"))

g <- seq(-0.6, 0.6, length.out = 9)
grid <- cbind(rep(g, 9), rep(g, each = 9))
frame <- data.frame(x = grid[seq(1, 81, by = 8), 1] + 0.05,
                    y = grid[seq(1, 81, by = 8), 2] - 0.03)
bad_frame <- list(a = frame$x, b = frame$y)
outside <- cbind(c(2, 0.1), c(2, -0.2))
three_cols <- cbind(grid[, 1], grid[, 2], 1)

out <- character(0)
add <- function(line) out <<- c(out, line)

run_case <- function(name, newdata) {
  add(paste("CASE", name))
  res <- tryCatch(predict.qss2(obj, newdata = newdata), error = function(e) e)
  if (inherits(res, "error")) {
    add(paste("ERR", conditionMessage(res)))
    return(invisible(NULL))
  }
  add(paste(c("x", length(res$x), sprintf("%.17g", as.numeric(res$x))), collapse = " "))
  add(paste(c("y", length(res$y), sprintf("%.17g", as.numeric(res$y))), collapse = " "))
  add(paste(c("z", length(res$z), sprintf("%.17g", as.numeric(res$z))), collapse = " "))
  D <- as.matrix(res$D)
  add(paste(c("D", nrow(D), ncol(D), sprintf("%.17g", as.vector(t(D)))), collapse = " "))
  invisible(res)
}

run_case("matrix_grid", grid)
run_case("list_frame", frame)
midpoints <- (X[10:20, ] + X[11:21, ]) / 2
run_case("pair_midpoints", midpoints)
run_case("names_conflict", bad_frame)
run_case("outside_hull", outside)
run_case("three_columns", three_cols)

writeLines(out, file.path(out_dir, "predict.qss2-r.txt"))

one <- function() predict.qss2(obj, newdata = grid)
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(out_dir, "predict.qss2-r-time.txt"))
cat("ok predict.qss2\n")
