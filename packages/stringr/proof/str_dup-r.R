.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

fruit <- c("apple", "pear", "banana")
writeLines(
  c(
    paste0("str_dup(fruit, 2) returns ", paste(str_dup(fruit, 2), collapse = ", "), "."),
    paste0("str_dup(fruit, 1:3) returns ", paste(str_dup(fruit, 1:3), collapse = ", "), "."),
    paste0(
      "str_dup(c(\"a\", NA), 2, sep = \"-\") returns ",
      paste(str_dup(c("a", NA), 2, sep = "-"), collapse = ", "),
      "."
    )
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_dup-r.txt"
)

norm <- function(x) {
  if (is.null(x)) return(list())
  if (is.list(x)) {
    out <- lapply(x, norm)
    if (is.null(names(x))) return(out)
    return(list(data = unname(out), names = names(x)))
  }
  if (is.null(names(x))) return(unname(x))
  list(data = unname(x), names = names(x))
}

one <- function() {
  list(
    main = str_dup(rep(fruit, 40), 2),
    sep = str_dup(fruit, 2, sep = " "),
    times = str_dup(fruit, 1:3),
    na = str_dup(c("a", NA), 2),
    na_sep = str_dup(c("a", NA), 2, sep = "-"),
    zero = str_dup(c("a", NA), 0),
    zero_sep = str_dup(c("a", NA), 0, sep = "-"),
    negative = str_dup("a", -1),
    na_times = str_dup("a", NA),
    null_long = str_dup(NULL, 1:3),
    empty_one = str_dup(character(), 1),
    string_null = str_dup("a", NULL),
    float = str_dup("ab", 2.9),
    float_sep = str_dup(c("ab", "cd"), c(1.2, 2.9), sep = "-"),
    logical = str_dup("ab", TRUE),
    names = str_dup(c(x = "ab", y = "cd"), 2),
    names_recycle = str_dup(c(a = "ab"), 1:3),
    both_null = str_dup(NULL, NULL),
    both_empty = str_dup(character(), integer())
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
body <- jsonlite::toJSON(lapply(value, norm), auto_unbox = FALSE, na = "null", null = "null", digits = 16)
ms <- jsonlite::toJSON(median(elapsed) * 1000, auto_unbox = TRUE, digits = 16)
cat(paste0("{\"value\":", body, ",\"median_ms\":", ms, "}\n"))
