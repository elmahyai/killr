.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

x <- c("abcde", "ghifgh")
parts <- str_sub_all(x, c(1, 2), c(2, 4))
writeLines(
  paste0(
    "str_sub_all(x, c(1, 2), c(2, 4)) returns ",
    paste(vapply(parts, function(item) paste(item, collapse = " "), ""), collapse = " | "),
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_sub_all-r.txt"
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

pos <- matrix(c(2, 6, 5, 7), ncol = 2, dimnames = list(NULL, c("start", "end")))
lenm <- matrix(c(1, 2, 3, 2), ncol = 2, dimnames = list(NULL, c("start", "length")))
block <- rep(c("abcde", "ghifgh"), 40)

one <- function() {
  list(
    main = str_sub_all(block, c(1, 2), c(2, 4)),
    pair = str_sub_all(x, c(1, 2), c(2, 4)),
    one = str_sub_all("abcdef", c(1, 3), c(2, 5)),
    matrix = str_sub_all(x, pos),
    length_matrix = str_sub_all("abcdef", lenm),
    per_string = str_sub_all(c("abcdef", "ghijkl"), list(c(1, 3), c(2, 4)), -1),
    names = str_sub_all(c(a = "abcd", b = "efgh"), 1, 2),
    empty = str_sub_all(character(), 1:2, 2:3)
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
