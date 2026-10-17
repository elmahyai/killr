suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


shown <- c("a", NA) %stri+% c("b", "c")
writeLines(
  paste0(
    "c('a', NA) %stri+% c('b', 'c') returns ",
    paste(ifelse(is.na(shown), "NA", shown), collapse = ", "),
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%stri+%-r.txt"
)

one <- function() {
  list(
    id = "ID_" %stri+% 1:3,
    na = c("a", NA) %stri+% c("b", "c"),
    text = c("NA", NA) %stri+% "x",
    empty = "" %stri+% NULL
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
