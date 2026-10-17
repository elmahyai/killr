.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
pdf(tempfile(fileext = ".pdf"))

# Fixed inputs with no random draws. NA cells are fixed; dataImp fills each
# missing cell with the mean of the observed values in its column.
make_data <- function() {
  t <- 1:12
  x <- cbind(t / 4 + sin(t), cos(t * 0.7) * 3, ((t^2) %% 7) / 2)
  x[2, 1] <- NA
  x[5, 2] <- NA
  x[9, 3] <- NA
  x[11, 1] <- NA
  x
}
impute_mean <- function(x) {
  m <- colMeans(x, na.rm = TRUE)
  for (j in seq_len(ncol(x))) x[is.na(x[, j]), j] <- m[j]
  x
}

out <- character(0)
emit <- function(...) out <<- c(out, paste(..., sep = " "))
num <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = " ")
rec_panel <- function(tag) {
  function(x, y, pch, col, ...) {
    emit("panel", tag, "usr", num(par("usr")), "pch", num(pch),
         "col", paste(col, collapse = " "), "x", num(x), "y", num(y))
  }
}
rec_text <- function(x, y, txt, cex, font) {
  emit("label", num(x), num(y), txt, "usr", num(par("usr")),
       "cex", num(cex), "font", num(font))
}

run_case <- function(extra) {
  out <<- character(0)
  d <- make_data()
  di <- impute_mean(d)
  args <- c(list(data = d, dataImp = di,
                 lower.panel = rec_panel("lower"),
                 upper.panel = rec_panel("upper"),
                 text.panel = rec_text,
                 cex.labels = 1), extra)
  do.call(imputePairs, args)
  out
}

one <- function() {
  c(paste("case A row1attop TRUE"), run_case(list(labels = c("alpha", "beta", "gamma"), row1attop = TRUE)),
    paste("case B row1attop FALSE"), run_case(list(labels = c("alpha", "beta", "gamma"), row1attop = FALSE)),
    paste("case C labels NULL"), run_case(list(labels = NULL)),
    paste("case D labels missing"), run_case(list()))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "\n")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
invisible(dev.off())
