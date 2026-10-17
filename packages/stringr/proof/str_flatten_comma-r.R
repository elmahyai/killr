.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

writeLines(
  c(
    paste0("str_flatten_comma(letters[1:3], \", and \") returns ", str_flatten_comma(letters[1:3], ", and "), "."),
    paste0("str_flatten_comma(letters[1:2], \", and \") returns ", str_flatten_comma(letters[1:2], ", and "), ".")
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_flatten_comma-r.txt"
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
    main = str_flatten_comma(rep(letters[1:4], 30), ", and "),
    three = str_flatten_comma(letters[1:3], ", and "),
    two = str_flatten_comma(letters[1:2], ", and "),
    one = str_flatten_comma("a", ", and "),
    empty = str_flatten_comma(character(), ", and "),
    na_pair = str_flatten_comma(c("a", NA), ", and "),
    na_rm = str_flatten_comma(c("a", NA), ", and ", na.rm = TRUE),
    no_comma = str_flatten_comma(letters[1:3], " and "),
    comma_only = str_flatten_comma(letters[1:2], ","),
    or_last = str_flatten_comma(letters[1:3], ", or "),
    four = str_flatten_comma(letters[1:4], ", and ")
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
