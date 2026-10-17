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
writeLines(c(
  str_replace(fruits, "[aeiou]", "-"),
  str_replace(fruits, "([aeiou])", "\\1\\1"),
  str_replace(fruits, "[aeiou]", c("1", "2", "3")),
  str_replace(fruits, c("a", "e", "i"), "-")
), file.path(out, "str_replace-r.txt"), useBytes = TRUE)

bulk <- rep(fruits, 400)
named_in <- c(C = "3", B = "2", A = "1")

one <- function() {
  named <- str_replace(named_in, "[0-9]", "x")
  list(
    dash = str_replace(fruits, "[aeiou]", "-"),
    back = str_replace(fruits, "([aeiou])", "\\1\\1"),
    vec = str_replace(fruits, "[aeiou]", c("1", "2", "3")),
    pat = str_replace(fruits, c("a", "e", "i"), "-"),
    fixed = str_replace("x.x", fixed("."), "Y"),
    coll = str_replace("\u0131", coll("I", ignore_case = TRUE, locale = "tr"), "Y"),
    na = str_replace("xx", "x", NA_character_),
    fun = str_replace("abc", "a|c", toupper),
    fun_na = str_replace("abc", "b", function(xs) rep(NA_character_, length(xs))),
    zero = str_replace("abc", "$", toupper),
    empty_pat = str_replace("abc", "", toupper),
    num = str_replace(c(1, 12), "1", "X"),
    names = names(named),
    named_values = unname(named),
    long = str_replace(bulk, "[aeiou]", "-")
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
