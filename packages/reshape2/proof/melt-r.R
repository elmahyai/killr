.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(reshape2))
stopifnot(as.character(packageVersion("reshape2")) == "1.4.5")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

example_path <- file.path(out_dir, "melt-r.txt")
sink(example_path)
example("melt.array", package = "reshape2", ask = FALSE)
example("melt.list", package = "reshape2", ask = FALSE)
example("melt.data.frame", package = "reshape2", ask = FALSE)
sink()

# 4000 rows, two id columns and two numeric measures, some missing.
n <- 4000L
i <- 0:(n - 1L)
frame <- data.frame(
  id = i + 1L,
  group = paste0("g", i %% 5L),
  a = ifelse(i %% 11L == 0L, NA_real_, (i %% 97L) / 2),
  b = ifelse(i %% 13L == 0L, NA_real_, as.numeric((i * 3L) %% 50L)),
  stringsAsFactors = FALSE
)

one <- function() {
  melt(frame, id = c("id", "group"))
}

value <- one()
elapsed <- numeric(20)
for (step in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step]] <- as.numeric(Sys.time()) - t0
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
