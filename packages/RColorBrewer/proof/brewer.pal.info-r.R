.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(RColorBrewer))
stopifnot(packageDescription("RColorBrewer")$Version == "1.1-3")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
root <- normalizePath(file.path(dirname(script), ".."))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

json_str <- function(s) {
  if (length(s) != 1) return("null")
  bytes <- as.integer(charToRaw(enc2utf8(s)))
  parts <- character(length(bytes))
  for (i in seq_along(bytes)) {
    b <- bytes[[i]]
    parts[[i]] <- if (b == 34) paste0("\\", '"')
      else if (b == 92) paste0("\\", "\\")
      else if (b == 10) paste0("\\", "n")
      else if (b == 13) paste0("\\", "r")
      else if (b == 9) paste0("\\", "t")
      else if (b < 32 || b == 127) sprintf("\\u%04x", b)
      else intToUtf8(b)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

capture_example <- function() {
  out <- capture.output({
    print(brewer.pal.info)
    print(brewer.pal.info["Blues",])
    print(brewer.pal.info["Blues",]$maxcolors)
  })
  paste(out, collapse = "\n")
}

one <- function() {
  info <- brewer.pal.info
  c(
    as.integer(info$maxcolors),
    as.integer(info$colorblind),
    as.integer(brewer.pal.info["Blues",]$maxcolors)
  )
}

writeLines(capture_example(), file.path(out_dir, "brewer.pal.info-r.txt"))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

row_json <- function(name) {
  row <- brewer.pal.info[name, ]
  paste0(
    '{"name":', json_str(name),
    ',"maxcolors":', if (is.na(row$maxcolors)) "null" else as.integer(row$maxcolors),
    ',"category":', if (is.na(row$category)) "null" else json_str(as.character(row$category)),
    ',"colorblind":', if (is.na(row$colorblind)) "null" else tolower(as.character(row$colorblind)),
    "}"
  )
}

cases <- list(
  list(
    label = "full",
    rownames = rownames(brewer.pal.info),
    maxcolors = as.integer(brewer.pal.info$maxcolors),
    category = as.character(brewer.pal.info$category),
    colorblind = as.integer(brewer.pal.info$colorblind)
  ),
  list(
    label = "Blues",
    row = row_json("Blues")
  ),
  list(
    label = "Blues_maxcolors",
    value = as.integer(brewer.pal.info["Blues",]$maxcolors)
  ),
  list(
    label = "missing",
    row = row_json("nope")
  )
)

case_json <- function(item) {
  if (item$label == "full") {
    rn <- paste0("[", paste(vapply(item$rownames, json_str, ""), collapse = ","), "]")
    mc <- paste0("[", paste(item$maxcolors, collapse = ","), "]")
    cat <- paste0("[", paste(vapply(item$category, json_str, ""), collapse = ","), "]")
    cb <- paste0("[", paste(item$colorblind, collapse = ","), "]")
    paste0(
      '{"label":', json_str(item$label),
      ',"rownames":', rn,
      ',"maxcolors":', mc,
      ',"category":', cat,
      ',"colorblind":', cb, "}"
    )
  } else if (item$label == "Blues_maxcolors") {
    paste0(
      '{"label":', json_str(item$label),
      ',"value":', item$value, "}"
    )
  } else {
    paste0('{"label":', json_str(item$label), ',"row":', item$row, "}")
  }
}

value_json <- paste0("[", paste(value, collapse = ","), "]")
cases_json <- paste0("[", paste(vapply(cases, case_json, ""), collapse = ","), "]")
cat(sprintf(
  '{"value":%s,"cases":%s,"median_ms":%.17g}\n',
  value_json,
  cases_json,
  median(elapsed) * 1000
))
