.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(scales))
stopifnot(packageVersion("scales") == "1.4.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

one <- function() {
  number(
    c(12345.67, -8.2, 0, NA, Inf, -Inf, 2.5e5, 1.5e6),
    big.mark = ",",
    prefix = "$",
    style_negative = "parens",
    scale_cut = cut_short_scale()
  )
}

example <- capture.output(print(one()))
writeLines(example, file.path(out_dir, "number-r.txt"))

json_str <- function(s) {
  if (is.na(s)) return("null")
  chars <- strsplit(enc2utf8(s), "", fixed = TRUE)[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- character(length(value))
for (i in seq_along(value)) parts[[i]] <- json_str(value[[i]])
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(parts, collapse = ","),
  median(elapsed) * 1000
))
