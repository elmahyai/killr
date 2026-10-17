.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
if (as.character(packageVersion("stringr")) != "1.6.0") stop("stringr version")
if (as.character(packageVersion("stringi")) != "1.8.9") stop("stringi version")

json_string <- function(s) {
  cps <- utf8ToInt(s)
  if (length(cps) == 0) return("\"\"")
  parts <- character(length(cps))
  for (i in seq_along(cps)) {
    cp <- cps[[i]]
    if (cp == 34) parts[[i]] <- "\\\""
    else if (cp == 92) parts[[i]] <- "\\\\"
    else if (cp == 10) parts[[i]] <- "\\n"
    else if (cp == 13) parts[[i]] <- "\\r"
    else if (cp == 9) parts[[i]] <- "\\t"
    else if (cp < 32) parts[[i]] <- sprintf("\\u%04x", as.integer(cp))
    else parts[[i]] <- intToUtf8(cp)
  }
  paste0("\"", paste(parts, collapse = ""), "\"")
}

json_chars <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    if (is.na(x[[i]])) parts[[i]] <- "null" else parts[[i]] <- json_string(x[[i]])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}

json_value <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x)) {
    keys <- names(x)
    parts <- character(length(x))
    for (i in seq_along(x)) {
      parts[[i]] <- paste0(json_string(keys[[i]]), ":", json_value(x[[i]]))
    }
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  if (is.character(x)) return(json_chars(x))
  stop(paste("unsupported", paste(class(x), collapse = ",")))
}

fruits <- c("one apple", "two pears", "three bananas")
out <- "/home/ahmed/killr_projects/killr/packages/stringr/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)
writeLines(
  str_remove_all(fruits, "[aeiou]"),
  file.path(out, "str_remove_all-r.txt"),
  useBytes = TRUE
)

bulk <- rep(fruits, 200)

one <- function() {
  list(
    all = str_remove_all(fruits, "[aeiou]"),
    via = str_replace_all(fruits, "[aeiou]", ""),
    upper = str_replace_all("abc", "a|c", toupper),
    removed = str_remove_all("abc", "a|c"),
    fixed = str_remove_all("x.x.", fixed(".")),
    long = str_remove_all(bulk, "[aeiou]")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(
  "{\"value\":", json_value(value),
  ",\"median_ms\":", sprintf("%.17g", median(elapsed) * 1000),
  "}\n"
))
