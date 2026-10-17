# Shared fixtures and record writer for the BIC proofs (mclust 6.1.3).
# Run from packages/mclust:  Rscript proof/<name>-r.R
suppressMessages(library(mclust))

models14 <- c("EII", "VII", "EEI", "VEI", "EVI", "VVI", "EEE",
              "VEE", "EVE", "VVE", "EEV", "VEV", "EVV", "VVV")

# Fixed synthetic BIC grid. Values are multiples of 0.25 (exact in binary),
# so the same numbers are built in R and Python. Cells with (G + j) %% 7 == 0
# are NA, and the repeated (G * j) %% 5 term produces ties.
fixture <- function(gvals, jidx, models) {
  I <- matrix(as.numeric(gvals), nrow = length(gvals), ncol = length(jidx))
  J <- matrix(as.numeric(jidx), nrow = length(gvals), ncol = length(jidx),
              byrow = TRUE)
  m <- -1000 - (I * 0.5 + ((I * J) %% 5) * 2.5 + J * 0.25)
  m[(I + J) %% 7 == 0] <- NA
  dimnames(m) <- list(as.character(gvals), models)
  m
}

# A mclustBIC-like object: matrix with the attributes the R code reads.
bic_obj <- function(gvals, jidx, models, n, d, tag, cls = "mclustBIC",
                    noise = FALSE) {
  m <- fixture(gvals, jidx, models)
  attributes(m) <- c(attributes(m), list(
    n = n, d = d, tag = tag, class = cls, criterion = "BIC",
    returnCodes = matrix(0L, nrow(m), ncol(m), dimnames = dimnames(m))))
  if (noise) attr(m, "noise") <- TRUE
  m
}

fmt <- function(x) {
  x <- as.numeric(x)
  ifelse(is.na(x), "NA", sprintf("%.17g", x))
}

tok <- function(a) {
  if (is.null(a)) return("NULL")
  if (is.numeric(a)) return(fmt(a))
  paste(a, collapse = ",")
}

line <- function(key, vals) paste(c(key, vals), collapse = "\t")

# Record for a matrix result (or NULL). Mirrors record_matrix in
# bic_proof_common.py.
matrix_record <- function(id, x) {
  out <- paste0("case\t", id)
  if (is.null(x)) return(c(out, "null\t1"))
  v <- unclass(x)
  out <- c(out, line("dim", fmt(dim(v))))
  out <- c(out, line("G", fmt(as.numeric(rownames(v)))))
  out <- c(out, line("modelNames", colnames(v)))
  out <- c(out, line("n", tok(attr(v, "n"))), line("d", tok(attr(v, "d"))))
  out <- c(out, line("tag", tok(attr(v, "tag"))))
  out <- c(out, line("criterion", tok(attr(v, "criterion"))))
  out <- c(out, line("class", tok(class(x))))
  for (i in seq_len(nrow(v))) out <- c(out, line("row", fmt(v[i, ])))
  out
}

# Median of the timed calls, in milliseconds (Sys.time). The untimed call is
# the one that builds the records, so it is not repeated here.
time_median_ms <- function(fn, reps = 20) {
  t <- numeric(reps)
  for (r in seq_len(reps)) {
    t0 <- Sys.time()
    invisible(fn())
    t[r] <- as.numeric(Sys.time() - t0, units = "secs") * 1000
  }
  median(t)
}

write_record <- function(name, lines, ms) {
  dir.create(file.path("docs", "output"), recursive = TRUE, showWarnings = FALSE)
  writeLines(c(lines, paste0("time_ms\t", fmt(ms))),
             file.path("docs", "output", paste0(name, "-r.txt")))
}
