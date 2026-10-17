.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

hw <- "Hadley Wickham"
writeLines(
  c(
    paste0("str_sub(hw, 1, 6) returns ", str_sub(hw, 1, 6), "."),
    paste0("str_sub(hw, -7) returns ", str_sub(hw, -7), "."),
    paste0("str_sub(hw, c(1, 8), c(6, 14)) returns ", paste(str_sub(hw, c(1, 8), c(6, 14)), collapse = ", "), ".")
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_sub-r.txt"
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
block <- rep(c("Hadley Wickham", "abcde", NA, ""), 30)

one <- function() {
  list(
    main = str_sub(block, 1, 4),
    head = str_sub(hw, 1, 6),
    end_only = str_sub(hw, end = 6),
    tail = str_sub(hw, -7),
    vec = str_sub(hw, c(1, 8), c(6, 14)),
    two = str_sub(c("abcde", "ghifgh"), c(1, 2), c(2, 4)),
    matrix = str_sub(hw, pos),
    length_matrix = str_sub("abcdef", lenm),
    empty = str_sub(character(), 1, 2),
    na_string = str_sub(c("abc", NA), 1, 2),
    na_index = str_sub("abc", NA, 2),
    past = str_sub("abc", 10, 12),
    before = str_sub("abc", 3, 1),
    zero = str_sub("abc", 0, 2),
    named = str_sub(c(a = "abcdef", b = "ghijkl"), 1, 2),
    named_recycled = str_sub(c(a = "abcdef"), c(1, 2), c(2, 3)),
    null = str_sub(NULL)
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
