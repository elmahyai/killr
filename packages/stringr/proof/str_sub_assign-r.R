.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

x <- "BBCDEF"
str_sub(x, 1, 1) <- "A"
str_sub(x, -1, -1) <- "K"
str_sub(x, -2, -2) <- "GHIJ"
str_sub(x, 2, -2) <- ""
writeLines(
  paste0("str_sub<- on BBCDEF returns ", x, "."),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_sub<--r.txt"
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

chain <- function(text) {
  str_sub(text, 1, 1) <- "A"
  str_sub(text, -1, -1) <- "K"
  str_sub(text, -2, -2) <- "GHIJ"
  str_sub(text, 2, -2) <- ""
  text
}

one <- function() {
  y <- c("abcd", NA)
  str_sub(y, 1, 1, omit_na = TRUE) <- "Z"
  z <- c("abcd", NA)
  str_sub(z, 1, 1) <- "Z"
  recycled <- c("abcd", "efgh")
  str_sub(recycled, 1, 1) <- "Z"
  matrix_value <- c("abcdef", "ghijkl")
  str_sub(matrix_value, matrix(c(1, 2, 2, 3), ncol = 2)) <- c("X", "YZ")
  kept <- "abcdef"
  str_sub(kept, NA, 2, omit_na = TRUE) <- "Z"
  dropped <- "abcdef"
  str_sub(dropped, NA, 2) <- "Z"
  block <- rep(c("BBCDEF", "abcdef"), 40)
  str_sub(block, 1, 1) <- "Q"
  list(
    main = block,
    chain = chain("BBCDEF"),
    omit = y,
    no_omit = z,
    recycle = recycled,
    matrix = matrix_value,
    omit_index = kept,
    drop_index = dropped
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
