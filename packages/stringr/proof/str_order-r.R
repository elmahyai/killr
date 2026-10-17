.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

json_str <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  paste0('"', s, '"')
}

json_atom <- function(x) {
  n <- length(x)
  if (n == 0) return("[]")
  parts <- character(n)
  if (is.logical(x)) {
    for (i in seq_len(n)) {
      if (is.na(x[[i]])) parts[[i]] <- "null"
      else if (isTRUE(x[[i]])) parts[[i]] <- "true"
      else parts[[i]] <- "false"
    }
  } else if (is.integer(x)) {
    for (i in seq_len(n)) {
      if (is.na(x[[i]])) parts[[i]] <- "null"
      else parts[[i]] <- as.character(x[[i]])
    }
  } else if (is.numeric(x)) {
    for (i in seq_len(n)) {
      if (is.na(x[[i]])) parts[[i]] <- "null"
      else parts[[i]] <- sprintf("%.17g", x[[i]])
    }
  } else if (is.character(x)) {
    for (i in seq_len(n)) {
      if (is.na(x[[i]])) parts[[i]] <- "null"
      else parts[[i]] <- json_str(x[[i]])
    }
  } else {
    stop(paste("unsupported", paste(class(x), collapse = "/")))
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

json_one <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x)) {
    nms <- names(x)
    if (is.null(nms)) {
      if (length(x) == 0) return("[]")
      parts <- vapply(x, json_one, character(1))
      return(paste0("[", paste(parts, collapse = ","), "]"))
    }
    parts <- character(length(x))
    for (i in seq_along(x)) {
      parts[[i]] <- paste0(json_str(nms[[i]]), ":", json_one(x[[i]]))
    }
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  json_atom(x)
}

base <- c(
  "apple", "car", "happy", "char",
  "100a10", "100a5", "2b", "2a",
  "a", "A", "b", "B",
  NA, "", "NA",
  "\ufeffabc", "abc",
  "cote", "c\u00f4te", "cot\u00e9", "c\u00f4t\u00e9",
  "motley", "m\u00f6tley",
  "10", "2", "100"
)
long <- rep(base, 40)

one <- function() list(
  main = str_order(long),
  cs = str_order(c("apple", "car", "happy", "char"), locale = "cs"),
  num = str_order(c("2", "1", "10"), numeric = TRUE),
  lex = str_order(c("2", "1", "10")),
  dec = str_order(c("a", "b", "a"), decreasing = TRUE),
  drop = str_order(c("b", NA, "a"), na_last = NA),
  first = str_order(c("b", NA, "a"), na_last = FALSE),
  last = str_order(c("b", NA, "a"), na_last = TRUE),
  bom = str_order(c("\ufeffabc", "abc", "b", NA, "a")),
  ties = str_order(c("b", "a", "b", "a")),
  empty = str_order(character())
)

out_dir <- "/home/ahmed/killr_projects/killr/packages/stringr/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(
  "str_order(c(\"apple\", \"car\", \"happy\", \"char\")) returns 1, 2, 4, 3.",
  file.path(out_dir, "str_order-r.txt")
)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0('{"value":', json_one(value), ',"median_ms":', sprintf("%.17g", median(elapsed) * 1000), '}\n'))
