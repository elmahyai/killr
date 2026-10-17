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

one <- function() brewer.pal(7, "Greens")
value <- one()
writeLines(
  paste0('brewer.pal(7, "Greens") returns ', paste(value, collapse = " "), "."),
  file.path(out_dir, "brewer.pal-r.txt")
)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

run <- function(label, n, name) {
  warns <- character()
  result <- tryCatch(
    withCallingHandlers(
      brewer.pal(n, name),
      warning = function(w) {
        warns <<- c(warns, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) structure(conditionMessage(e), class = "bp_error")
  )
  warn <- if (length(warns) == 0) NULL else paste(warns, collapse = "")
  if (inherits(result, "bp_error")) {
    list(label = label, colors = NULL, warning = warn, error = as.character(result)[[1]])
  } else {
    list(label = label, colors = as.character(result), warning = warn, error = NULL)
  }
}

case_json <- function(item) {
  colors <- if (is.null(item$colors)) {
    "null"
  } else {
    paste0("[", paste(vapply(item$colors, json_str, ""), collapse = ","), "]")
  }
  warning <- if (is.null(item$warning)) "null" else json_str(item$warning)
  error <- if (is.null(item$error)) "null" else json_str(item$error)
  paste0(
    '{"label":', json_str(item$label),
    ',"colors":', colors,
    ',"warning":', warning,
    ',"error":', error, "}"
  )
}

cases <- list()
push <- function(label, n, name) {
  cases[[length(cases) + 1]] <<- run(label, n, name)
}

info <- brewer.pal.info
for (name in rownames(info)) {
  limit <- info[name, "maxcolors"]
  for (n in 3:limit) push(paste0(name, ":", n), n, name)
  push(paste0(name, ":max+1"), limit + 1L, name)
}
push("min:1:Blues", 1, "Blues")
push("min:2:Blues", 2, "Blues")
push("min:0:Blues", 0, "Blues")
push("min:-1:Set1", -1, "Set1")
push("min:-Inf:Blues", -Inf, "Blues")
push("min:2.999:Greens", 2.999, "Greens")
push("max:100:Blues", 100, "Blues")
push("max:Inf:Blues", Inf, "Blues")
push("max:1e20:Set3", 1e20, "Set3")
push("trunc:3.9:Greens", 3.9, "Greens")
push("trunc:8.2:Blues", 8.2, "Blues")
push("trunc:8.999:Blues", 8.999, "Blues")
push("int:Greens", 7L, "Greens")
push("vec:Greens", c(7), "Greens")
push("namevec:Greens", 7, c("Greens"))
push("true:Blues", TRUE, "Blues")
push("false:Reds", FALSE, "Reds")
push("bad:nope", 5, "nope")
push("bad:Blue", 4, "Blue")
push("bad:blues", 4, "blues")
push("bad:empty", 4, "")
push("bad:NA", 5, NA_character_)
push("null:name", 5, NULL)
push("null:n", NULL, "Blues")
push("char:n", "7", "Greens")
push("len:n", c(4, 5), "Blues")
push("len:name", 4, c("Blues", "Reds"))
push("na:n", NA_real_, "Blues")
push("nan:n", NaN, "Set1")

value_json <- paste0("[", paste(vapply(value, json_str, ""), collapse = ","), "]")
cases_json <- paste0("[", paste(vapply(cases, case_json, ""), collapse = ","), "]")
cat(sprintf(
  '{"value":%s,"cases":%s,"median_ms":%.17g}\n',
  value_json,
  cases_json,
  median(elapsed) * 1000
))
