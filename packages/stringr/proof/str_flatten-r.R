.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

writeLines(
  c(
    paste0("str_flatten(letters[1:3], \", \", \" and \") returns ", str_flatten(letters[1:3], ", ", " and "), "."),
    paste0("str_flatten(letters[1:2], \", \", \", and \") returns ", str_flatten(letters[1:2], ", ", ", and "), ".")
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_flatten-r.txt"
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
    main = str_flatten(rep(letters, 4), "-"),
    last = str_flatten(letters[1:3], ", ", " and "),
    oxford = str_flatten(letters[1:2], ", ", ", and "),
    na = str_flatten(c("a", NA, "b")),
    na_rm = str_flatten(c("a", NA, "b"), na.rm = TRUE),
    last_na = str_flatten(c("a", NA), ", ", " and "),
    empty = str_flatten(character()),
    null = str_flatten(NULL),
    na_only = str_flatten(NA),
    all_na_rm = str_flatten(c(NA, NA), na.rm = TRUE),
    last_empty = str_flatten(c("a", "b"), "-", ""),
    numbers = str_flatten(1:3, "-", " and ")
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
