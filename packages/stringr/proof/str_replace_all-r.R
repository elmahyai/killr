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
joined <- paste(fruits, collapse = "---")
out <- "/home/ahmed/killr_projects/killr/packages/stringr/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)
na_row <- str_replace_all(fruits, "b", NA_character_)
writeLines(c(
  str_replace_all(fruits, "[aeiou]", "-"),
  str_replace_all(fruits, "[aeiou]", toupper),
  na_row,
  str_replace_all(joined, c(one = "1", two = "2", three = "3"))
), file.path(out, "str_replace_all-r.txt"), useBytes = TRUE)

bulk <- rep(fruits, 200)
bulk_fun <- rep(fruits, 80)

one <- function() {
  list(
    dash = str_replace_all(fruits, "[aeiou]", "-"),
    fun = str_replace_all(fruits, "[aeiou]", toupper),
    na = str_replace_all(fruits, "b", NA_character_),
    named = str_replace_all(joined, c(one = "1", two = "2", three = "3")),
    zero = str_replace_all("abc", "$|^", function(xs) rep("X", length(xs))),
    bound = str_replace_all("x x", boundary("word"), toupper),
    empty_pat = str_replace_all("abc", "", toupper),
    fixed = str_replace_all("x.x.", fixed("."), "Y"),
    coll = str_replace_all("\u0131I", coll("I", ignore_case = TRUE, locale = "tr"), "Y"),
    multi = str_replace_all(c("ab", "ba"), c(a = "A", b = "B")),
    group = str_replace_all("abcde", "(b)(c)(d)", "\\2"),
    na_fun = str_replace_all(c("ab", NA, "c"), "a|c", toupper),
    long = str_replace_all(bulk, "[aeiou]", "-"),
    long_fun = str_replace_all(bulk_fun, "[aeiou]", toupper)
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
