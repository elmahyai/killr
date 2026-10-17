.libPaths(c(path.expand("~/R/library"), .libPaths()))
stringi_189 <- function(lib) {
  desc <- file.path(lib, "stringi", "DESCRIPTION")
  if (!file.exists(desc)) return(FALSE)
  any(grepl("^Version:[[:space:]]*1\\.8\\.9[[:space:]]*$", readLines(desc, warn = FALSE)))
}
good <- Filter(stringi_189, .libPaths())
if (length(good)) .libPaths(unique(c(good[[1]], .libPaths())))
suppressPackageStartupMessages(library(stringi))
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
  } else if (is.numeric(x)) {
    for (i in seq_len(n)) {
      if (is.na(x[[i]])) parts[[i]] <- "null"
      else parts[[i]] <- format(x[[i]], scientific = FALSE, trim = TRUE)
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
    if (length(x) == 0) return("{}")
    parts <- character(length(x))
    for (i in seq_along(x)) {
      parts[[i]] <- paste0(json_str(nms[[i]]), ":", json_one(x[[i]]))
    }
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  json_atom(x)
}

base <- c(
  "hladny",
  "chladny",
  "Mario",
  "mario",
  "M\u00e1rio",
  "m\u00e1rio",
  "number2",
  "number100",
  "a",
  "A",
  "b",
  "B",
  NA,
  "",
  "NA",
  "\ufeffabc",
  "abc",
  "\u0105",
  "ff",
  "\ufb00",
  "cote",
  "c\u00f4te",
  "cot\u00e9",
  "c\u00f4t\u00e9",
  "G\u00e4rtner",
  "Gaertner",
  "above mentioned",
  "above-mentioned",
  "10",
  "2",
  "100",
  "\u00df",
  "gro\u00df",
  "GROSS"
)
left <- rep(base, 50)
right <- rep(rev(base), 50)

one <- function() list(
  main = `%s<=%`(left, right),
  short = `%s<=%`(c("a", "b", "A", "\ufeffa", NA), c("b", "b", "a", "a", "a"))
)

writeLines("'b' %s<=% 'b' returns TRUE.", "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%s<=%-r.txt")

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0('{"value":', json_one(value), ',"median_ms":', sprintf("%.17g", median(elapsed) * 1000), '}\n'))
