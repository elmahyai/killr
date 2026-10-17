suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- "ab" %stri*% 3
writeLines(
  paste0("'ab' %stri*% 3 returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%stri*%-r.txt"
)

one <- function() {
  list(
    rep = "ab" %stri*% 3,
    na = c("a", NA) %stri*% 2,
    seq = "a" %stri*% 1:5,
    text = c("NA", NA) %stri*% 2
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
