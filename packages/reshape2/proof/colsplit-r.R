.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(reshape2))
stopifnot(as.character(packageVersion("reshape2")) == "1.4.5")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

x <- c("a_1", "a_2", "b_2", "c_3")
vars <- colsplit(x, "_", c("trt", "time"))
example <- c(capture.output(print(vars)), capture.output(str(vars)))
writeLines(example, file.path(out_dir, "colsplit-r.txt"))

# 8000 strings: "g<group>_<time>_<amount>", a bare group, or NA.
n <- 8000L
string <- character(n)
for (k in 0:(n - 1L)) {
  if (k %% 17L == 0L) {
    string[[k + 1L]] <- NA_character_
  } else if (k %% 19L == 0L) {
    string[[k + 1L]] <- sprintf("g%d", k %% 11L)
  } else {
    string[[k + 1L]] <- sprintf("g%d_%d_%.1f", k %% 11L, k %% 100L, (k %% 50L) / 2)
  }
}

one <- function() {
  colsplit(string, "_", c("group", "time", "amount"))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

emit_col <- function(name, col) {
  if (is.factor(col)) {
    kind <- "factor"
    extra <- paste(levels(col), collapse = "|")
    vals <- ifelse(is.na(col), "NA", as.character(col))
  } else if (is.character(col)) {
    kind <- "character"
    extra <- ""
    vals <- ifelse(is.na(col), "NA", col)
  } else if (is.integer(col)) {
    kind <- "integer"
    extra <- ""
    vals <- ifelse(is.na(col), "NA", as.character(col))
  } else if (is.logical(col)) {
    kind <- "logical"
    extra <- ""
    vals <- ifelse(is.na(col), "NA", ifelse(col, "TRUE", "FALSE"))
  } else {
    kind <- "double"
    extra <- ""
    vals <- character(length(col))
    for (j in seq_along(col)) {
      if (is.nan(col[[j]])) vals[[j]] <- "NaN"
      else if (is.na(col[[j]])) vals[[j]] <- "NA"
      else if (is.infinite(col[[j]])) vals[[j]] <- if (col[[j]] > 0) "Inf" else "-Inf"
      else vals[[j]] <- sprintf("%.17g", col[[j]])
    }
  }
  cat("COL ", name, " ", kind, " ", extra, "\n", sep = "")
  cat(paste(vals, collapse = "\t"), "\n", sep = "")
}

cat(sprintf("MEDIAN_MS %.17g\n", median(elapsed) * 1000))
cat("NROW ", nrow(value), "\n", sep = "")
for (nm in names(value)) emit_col(nm, value[[nm]])
