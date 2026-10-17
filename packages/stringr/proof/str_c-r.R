.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

joined <- str_c("Letter", letters[1:3], sep = ": ")
missing <- str_c(c("a", NA, "b"), "-d")
writeLines(
  c(
    paste0("str_c(\"Letter\", letters[1:3], sep = \": \") returns ", paste(joined, collapse = ", "), "."),
    paste0(
      "str_c(c(\"a\", NA, \"b\"), \"-d\") returns ",
      paste(ifelse(is.na(missing), "NA", missing), collapse = ", "),
      "."
    )
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_c-r.txt"
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
    main = str_c(rep(letters, 5), rep(LETTERS, 5), sep = "-"),
    nulls = str_c(NULL, "a", NULL, "b"),
    empty = str_c(),
    null_only = str_c(NULL),
    char0 = str_c("x", character()),
    na = str_c(c("a", NA, "b"), "-d"),
    collapse = str_c(letters[1:3], collapse = ", "),
    sep = str_c("Letter", letters[1:2], sep = ": "),
    one = str_c(c("a", "b")),
    numbers = str_c(1:2, c("x", "y")),
    collapse_empty = str_c(c("a", "b"), collapse = ""),
    collapse_of_empty = str_c(character(), collapse = ","),
    collapse_only = str_c(collapse = ",")
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
