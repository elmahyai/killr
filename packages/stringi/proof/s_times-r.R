suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


example <- "ab" %s*% 3
writeLines(
  paste0("'ab' %s*% 3 returns ", example, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/%s*%-r.txt"
)

one <- function() {
  list(
    rep = "ab" %s*% 3,
    na = c("a", NA) %s*% 2,
    seq = "a" %s*% 1:5,
    text = c("NA", NA) %s*% 2
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
