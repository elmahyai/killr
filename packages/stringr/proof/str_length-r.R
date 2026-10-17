.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

x <- str_length(c("i", "like", "programming", NA))
u <- str_length(c("\u00fc", "u\u0308"))
writeLines(
  c(
    paste0(
      "str_length(c(\"i\", \"like\", \"programming\", NA)) returns ",
      paste(ifelse(is.na(x), "NA", x), collapse = ", "),
      "."
    ),
    paste0(
      "str_length of u-umlaut and u plus accent returns ",
      paste(u, collapse = ", "),
      "."
    )
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_length-r.txt"
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

base <- c("abc", NA, "", "NA", "\u00fc", "u\u0308", "\u6c49\u5b57", "\U0001f60a", "\u0105")

one <- function() {
  list(
    main = str_length(rep(base, 40)),
    scalar = str_length("abc"),
    na = str_length(NA),
    empty = str_length(character()),
    null = str_length(NULL),
    named = str_length(c(a = "ab", b = NA)),
    numbers = str_length(c(1, 1.5, NA)),
    logical = str_length(c(TRUE, FALSE, NA))
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
