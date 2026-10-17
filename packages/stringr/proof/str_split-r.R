.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

esc <- function(x) {
  x <- enc2utf8(x)
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\t", "\\t", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

atom <- function(x) {
  if (is.character(x)) {
    if (is.na(x)) "null" else esc(x)
  } else if (is.logical(x)) {
    if (is.na(x)) "null" else if (isTRUE(x)) "true" else "false"
  } else if (is.numeric(x)) {
    if (is.na(x)) "null" else as.character(x)
  } else {
    stop("atom")
  }
}

vec <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(seq_along(x), function(i) atom(x[[i]]), ""), collapse = ","), "]")
}

encode <- function(x) {
  if (is.null(x)) return("null")
  if (is.matrix(x)) {
    if (nrow(x) == 0) return("[]")
    rows <- lapply(seq_len(nrow(x)), function(i) vec(x[i, ]))
    return(paste0("[", paste(rows, collapse = ","), "]"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    parts <- vapply(seq_along(x), function(i) encode(x[[i]]), "")
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  vec(x)
}

options(width = 120)
out <- "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_split-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
example_lines <- capture.output({
  fruits <- c(
    "apples and oranges and pears and bananas",
    "pineapples and mangos and guavas"
  )
  print(str_split(fruits, " and "))
  print(str_split(fruits, " and ", simplify = TRUE))
  print(str_split(fruits, " and ", n = 3))
  print(str_split(fruits, " and ", n = 2))
  print(str_split(fruits, " and ", n = 5))
})
writeLines(example_lines, out)

one <- function() {
  texts <- rep(c("apples and oranges and pears", "pineapples and mangos", NA, "", "a and "), 80)
  str_split(texts, " and ", n = 3)
}

stopifnot(identical(str_split("ab", "")[[1]], c("a", "b")))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(
  "{\"value\":", encode(value),
  ",\"median_ms\":", sprintf("%.17g", median(elapsed) * 1000),
  "}\n"
))
